# A very simply assembler

# SWAP $PC, [$SP+3]

from constants import *
from typing import *
from abc import abstractmethod
import re

from asm import assemble

def _rol(data: int) -> int:
    return ((data << 1) & 0xfffe) | ((data >> 15) & 1)

def _ror(data: int) -> int:
    return ((data >> 1) & 0x7fff) | ((data & 1) << 15)

def _make_signed(data: int, bit_count: int) -> int:
    mask = (1 << (bit_count + 1) - 1)
    mask2 = mask >> 1

    data &= mask
    if data <= mask2:
        return data
    else:
        return (data & mask2) - mask2 + 1

class Memory(object):
    def __init__(self, size: int):
        self.mem = {}
        self.size = size
    def set_base_addr(self, base_addr):
        self.base_addr = base_addr
    def get_size(self) -> int:
        return self.size
    def load(self, start_addr: int, content: Sequence[int]) -> None:
        assert start_addr >= self.base_addr
        assert start_addr < self.base_addr + self.size
        for ofs, data in enumerate(content):
            assert ofs + start_addr < self.base_addr + self.size
            self.mem[ofs+start_addr] = data
    def read(self, addr: int) -> int:
        assert addr >= self.base_addr
        assert addr < self.base_addr + self.size
        ret_val = self.mem.get(addr, None)
        # Read is destructive: once a location is read, it's cleared to 0,
        # But to be even more forceful, we remove the entry and the subsequent
        # write-back will ensure that we don't write a location that already exists
        try:
            del self.mem[addr]
        except KeyError:
            pass
        return ret_val
    def write(self, addr: int, data: int) -> None:
        assert addr >= self.base_addr
        assert addr < self.base_addr + self.size
        assert addr not in self.mem
        self.mem[addr] = data

class Bus(object):
    def __init__(self):
        self.clients = {}
    def register(self, base_addr: int, client: Any):
        assert base_addr not in self.clients
        client.set_base_addr(base_addr)
        size = client.get_size()
        for addr in range(base_addr, base_addr+size):
            self.clients[addr] = client
    def read(self, addr: int) -> int:
        return self.clients[addr].read(addr)
    def write(self, addr: int, data: int) -> None:
        self.clients[addr].write(addr, data)

class SimEventBase(object):
    def __init__(self):
        pass

class SimEventRead(SimEventBase):
    def __init__(self, addr: int, data: int):
        self.addr = addr
        self.data = data
    def __str__(self):
        return f"read MEM[0x{self.addr:04x}] returned 0x{self.data:04x}"

class SimEventWrite(SimEventBase):
    def __init__(self, addr: int, data: int):
        self.addr = addr
        self.data = data
    def __str__(self):
        return f"write MEM[0x{self.addr:04x}] to 0x{self.data:04x}"

class SimRegUpdate(SimEventBase):
    def __init__(self, reg_name: str, old_data: int, data: int):
        self.reg_name = reg_name
        self.old_data = old_data
        self.data = data
    def __str__(self):
        return f"reg {self.reg_name} updated from 0x{self.old_data:04x} to 0x{self.data:04x}"


class Processor(object):
    def __init__(self, bus: Bus, system: 'System'):
        self.bus = bus
        self.reset()
        system.register_for_clock(self)
        self.interrupt_pending = False

    def reset(self):
        self.pc = 0
        self.sp = 0
        self.r0 = 0
        self.r1 = 0
        self.inten = False
        self.in_reset = True
        self.events = []

    def set_interrupt(self, is_interrupt: bool):
        # This is intentionally asynchronous.
        self.interrupt_pending = is_interrupt

    def _read_mem(self, addr: int) -> int:
        data = self.bus.read(addr)
        self.events.append(SimEventRead(addr, data))
        return data

    def _write_mem(self, addr: int, data: int) -> None:
        self.bus.write(addr, data)
        self.events.append(SimEventWrite(addr, data))

    def _set_pc(self, data: int) -> None:
        self.events.append(SimRegUpdate("pc", self.pc, data))
        self.pc = data

    def _set_sp(self, data: int) -> None:
        self.events.append(SimRegUpdate("sp", self.sp, data))
        self.sp = data

    def _set_r0(self, data: int) -> None:
        self.events.append(SimRegUpdate("r0", self.r0, data))
        self.r0 = data

    def _set_r1(self, data: int) -> None:
        self.events.append(SimRegUpdate("r1", self.r1, data))
        self.r1 = data

    def _set_reg(self, inst_field_opa: int, data: int) -> None:
        if inst_field_opa == OPA_PC:
            self._set_pc(data)
        elif inst_field_opa == OPA_SP:
            self._set_sp(data)
        elif inst_field_opa == OPA_R0:
            self._set_r0(data)
        elif inst_field_opa == OPA_R1:
            self._set_r1(data)
        else:
            assert False

    def _get_reg_a(self, inst_field_opa: int) -> int:
        if inst_field_opa == OPA_PC:
            return self.pc
        elif inst_field_opa == OPA_SP:
            return self.sp
        elif inst_field_opa == OPA_R0:
            return self.r0
        elif inst_field_opa == OPA_R1:
            return self.r1
        else:
            assert False

    def _get_reg_b(self, inst_field_opb: int) -> int:
        if inst_field_opb == OPB_MEM_IMMED:
            return 0
        elif inst_field_opb == OPB_MEM_IMMED_PC:
            return self.pc
        elif inst_field_opb == OPB_MEM_IMMED_SP:
            return self.sp
        elif inst_field_opb == OPB_MEM_IMMED_R0:
            return self.r0
        elif inst_field_opb == OPB_IMMED:
            return 0
        elif inst_field_opb == OPB_IMMED_PC:
            return self.pc
        elif inst_field_opb == OPB_IMMED_SP:
            return self.sp
        elif inst_field_opb == OPB_IMMED_R0:
            return self.r0
        else:
            assert False

    def wait_clk(self):
        events = self.events
        self.events = []
        yield events

    def simulate(self):
        while True:
            if self.in_reset:
                new_pc = self._read_mem(0)
                yield from self.wait_clk()
                yield from self.wait_clk()
                self._set_pc(new_pc)
                yield from self.wait_clk()
                self.in_reset = False
            else:
                inst = self._read_mem(self.pc)
                yield from self.wait_clk()
                self._write_mem(self.pc, inst)
                yield from self.wait_clk()

                # Handle interrupts by overriding the just fetched instruction
                if self.interrupt_pending and self.inten:
                    inst = (INST_SWAP << OPCODE_OFS) | (0 << D_OFS) | (OPB_MEM_IMMED << OPB_OFS) | (OPA_PC << OPA_OFS) | (1 << IMMED_OFS)

                inst_field_opcode = (inst >> OPCODE_OFS) & 0xf
                inst_field_d = (inst >> D_OFS) & 0x1
                inst_field_opb = (inst >> OPB_OFS) & 0x7
                inst_field_opa = (inst >> OPA_OFS) & 3
                raw_inst_field_immed = (inst >> IMMED_OFS) & IMMED_MASK
                inst_field_immed = _make_signed(raw_inst_field_immed, IMMED_MASK.bit_length())
                mem_ref = inst_field_opb in (OPB_MEM_IMMED_PC, OPB_MEM_IMMED_SP, OPB_MEM_IMMED_R0, OPB_MEM_IMMED)
                mem_result = (inst_field_d == 1 or inst_field_opcode == INST_SWAP) and not inst_field_opcode in (INST_EQ,INST_LTU,INST_LTS,INST_LES,)
                reg_result = (inst_field_d == 0 or inst_field_opcode == INST_SWAP) and not inst_field_opcode in (INST_EQ,INST_LTU,INST_LTS,INST_LES,)
                alu_opa = None
                alu_opb = None
                mem_op_addr = self._get_reg_b(inst_field_opb) + inst_field_immed
                if mem_ref:
                    alu_opb = self._read_mem(mem_op_addr)
                else:
                    alu_opb = mem_op_addr
                alu_opa = self._get_reg_a(inst_field_opa)
                yield from self.wait_clk()

                if inst_field_opcode == INST_SWAP:
                    self._set_reg(inst_field_opa, alu_opb)
                    yield from self.wait_clk()
                if mem_ref and not mem_result:
                    self._write_mem(mem_op_addr, alu_opb)
                yield from self.wait_clk()

                # Execute (most) instructions here
                # Binary ops
                alu_result = None
                noskip = False
                if inst_field_opcode == INST_SWAP:
                    alu_result = alu_opa
                elif inst_field_opcode == INST_OR:
                    alu_result = alu_opa | alu_opb
                elif inst_field_opcode == INST_AND:
                    alu_result = alu_opa & alu_opb
                elif inst_field_opcode == INST_XOR:
                    alu_result = alu_opa ^ alu_opb
                elif inst_field_opcode == INST_ADD:
                    alu_result = (alu_opa + alu_opb) & 0xffff
                elif inst_field_opcode == INST_SUB:
                    alu_result = (alu_opa - alu_opb) & 0xffff
                elif inst_field_opcode == INST_ISUB:
                    alu_result = (alu_opb - alu_opa) & 0xffff
                # Unary ops:
                elif inst_field_opcode == INST_MOV:
                    if inst_field_d == 0:
                        alu_result = alu_opb
                    else:
                        alu_result = alu_opa
                elif inst_field_opcode == INST_ISTAT:
                    alu_result = 0 if self.inten else 2
                elif inst_field_opcode == INST_ROR:
                    if inst_field_d == 0:
                        alu_result = _ror(alu_opa)
                    else:
                        alu_result = _ror(alu_opb)
                elif inst_field_opcode == INST_ROL:
                    if inst_field_d == 0:
                        alu_result = _rol(alu_opa)
                    else:
                        alu_result = _rol(alu_opb)
                # Predicate ops (their inverse comes from the 'D' bit):
                elif inst_field_opcode == INST_EQ:
                    if inst_field_d == 0:
                        noskip = alu_opa == alu_opb
                    else:
                        noskip = alu_opa != alu_opb
                elif inst_field_opcode == INST_LTU:
                    if inst_field_d == 0:
                        noskip = alu_opa < alu_opb
                    else:
                        noskip = alu_opa >= alu_opb
                elif inst_field_opcode == INST_LTS:
                    if inst_field_d == 0:
                        noskip = _make_signed(alu_opa, 16) < _make_signed(alu_opb, 16)
                    else:
                        noskip = _make_signed(alu_opa, 16) >= _make_signed(alu_opb, 16)
                elif inst_field_opcode == INST_LES:
                    if inst_field_d == 0:
                        noskip = _make_signed(alu_opa, 16) <= _make_signed(alu_opb, 16)
                    else:
                        noskip = _make_signed(alu_opa, 16) > _make_signed(alu_opb, 16)
                else:
                    # We have one unused code, but I don't know yet what to do about it...
                    assert False
                if mem_result:
                    self._write_mem(mem_op_addr, alu_result)
                elif reg_result:
                    # The only case we have both of these set is SWAP/SWAPI and in
                    # those cases we've already done the register update in a previous
                    # clock cycle
                    self._set_reg(inst_field_opa, alu_result)
                yield from self.wait_clk()
                # Update PC
                self._set_pc(self.pc + (1 if noskip else 2))
                # Update inten
                if inst_field_opcode == INST_SWAP and inst_field_d == 0:
                    self.inten = not self.inten


class System(object):
    def __init__(self):
        self.clock_consumers = set()
        self.generators: Set[Generator] = set()
        self.mem = Memory(16384) # We have 16k of core memory
        self.bus = Bus()
        self.bus.register(0, self.mem)
        self.cpu = Processor(self.bus, self)

    def register_for_clock(self, client):
        if client not in self.clock_consumers:
            self.clock_consumers.add(client)

    def load_asm(self, asm: str) -> None:
        base_addr, words = assemble(asm)
        self.mem.load(base_addr, words)

    def load(self, base_addr: int, words: Sequence[int]) -> None:
        self.mem.load(base_addr, words)

    def simulate(self, clock_count: int) -> None:
        self.generators.clear()
        for consumer in self.clock_consumers:
            self.generators.add(consumer.simulate())
        for clk in range(clock_count+1):
            events = []
            for generator in self.generators:
                events += generator.send(None)
            print(f"======= CLK {clk} =========")
            for event in events:
                print("    " + str(event))



if __name__ == "__main__":
    sim = System()
    sim.load(0, (0x1000,)) # reset vector
    sim.load_asm(
"""
    .section TEXT 0x1000
    MOV $sp, 1
    MOV $r0, 2
    mov $r1, 3
    mov $pc, $pc
"""
    )
    sim.simulate(50)
