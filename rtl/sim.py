# A cycle-accurate simulator

from constants import *
from typing import *
from abc import abstractmethod
import re

from asm import assemble
from disasm import disasm_inst
from copy import copy

def _rol(data: int) -> int:
    return ((data << 1) & 0xfffe) | ((data >> 15) & 1)

def _ror(data: int) -> int:
    return ((data >> 1) & 0x7fff) | ((data & 1) << 15)

def _make_signed(data: int, bit_count: int) -> int:
    mask = (1 << bit_count) - 1
    is_negative = (data & (1 << (bit_count - 1))) != 0
    mask2 = mask >> 1

    data &= mask
    if is_negative:
        return (data & mask2) - mask2 - 1
    else:
        return data

class SimEventBase(object):
    def __init__(self):
        pass
    def act(self, simulator) -> None:
        pass

class SimEventTerminate(SimEventBase):
    def __init__(self, exit_code: int):
        self.exit_code = exit_code
    def act(self, simulator) -> None:
        simulator.terminate()
    def __str__(self) -> str:
        return f"TERMINATED WITH CODE: {self.exit_code}"
class SimEventMemDump(object):
    def __init__(self, memory: Dict[int, int]):
        self.memory = copy(memory)
    def __str__(self):
        prefix = "         "
        prev_addr = None
        dump = ""
        col_cnt = 0
        for addr in sorted(self.memory):
            data = self.memory[addr]
            if addr-1 != prev_addr or dump == "":
                # terminate what we've dumped previously and start anew
                dump_start = addr & 0xfff0
                dump += "\n" + prefix + _safe_format(dump_start) + ":"
                col_cnt = 0
                for i in range(dump_start, addr):
                    dump += " ----"
                    col_cnt += 1
                dump += f" {data:04x}" if data is not None else " xxxx"
                col_cnt += 1
            else:
                if col_cnt == 16:
                    dump += "\n" + prefix + _safe_format(dump_start) + ":"
                    col_cnt = 0
                dump += f" {data:04x}" if data is not None else " xxxx"
                col_cnt += 1
            prev_addr = addr
        dump += "\n"
        return dump


class Memory(object):
    def __init__(self, size: int, system: 'System'):
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

    def terminate(self) -> Sequence[SimEventBase]:
        return (SimEventMemDump(self.mem), )

class Terminator(object):
    def __init__(self, system: 'System'):
        system.register_for_clock(self)
        self.terminating = False
    def set_base_addr(self, base_addr):
        pass
    def get_size(self) -> int:
        return 1

    def read(self, addr: int) -> int:
        return 0
    def write(self, addr: int, data: int) -> None:
        self.terminating = True
        self.exit_code = data
    def simulate(self):
        while True:
            if self.terminating: yield (SimEventTerminate(self.exit_code), )
            yield []
    def terminate(self) -> Sequence[SimEventBase]:
        return []

class Bus(object):
    def __init__(self, system: 'System'):
        self.client_map = {}
        self.clients = set()
    def register(self, base_addr: int, client: Any):
        client.set_base_addr(base_addr)
        # We allow a client to be registered in multiple address regions (for aliasing)
        if client not in self.clients:
            self.clients.add(client)
        size = client.get_size()
        for addr in range(base_addr, base_addr+size):
            assert addr not in self.client_map
            self.client_map[addr] = client
    def read(self, addr: int) -> int:
        addr &= 0xffff
        return self.client_map[addr].read(addr)
    def write(self, addr: int, data: int) -> None:
        addr &= 0xffff
        self.client_map[addr].write(addr, data)
    def terminate(self) -> Sequence[SimEventBase]:
        ret_val = []
        for client in self.clients:
            ret_val += client.terminate()
        return ret_val

def _safe_format(data: Optional[int]) -> str:
    return f"0x{data&0xffff:04x}" if data is not None else "*NONE*"
class SimEventRead(SimEventBase):
    def __init__(self, addr: int, data: int):
        self.addr = addr
        self.data = data
    def __str__(self):
        return f"read MEM[{_safe_format(self.addr)}] returned {_safe_format(self.data)}"

class SimEventWrite(SimEventBase):
    def __init__(self, addr: int, data: int):
        self.addr = addr
        self.data = data
    def __str__(self):
        return f"write MEM[{_safe_format(self.addr)}] to {_safe_format(self.data)}"

class SimEventRegUpdate(SimEventBase):
    def __init__(self, reg_name: str, old_data: int, data: int):
        self.reg_name = reg_name
        self.old_data = old_data
        self.data = data
    def __str__(self):
        return f"reg {self.reg_name} updated from {_safe_format(self.old_data)} to {_safe_format(self.data)}"

class SimEventInstFetch(SimEventBase):
    def __init__(self, addr:int, data: int):
        self.addr = addr
        self.data = data
    def __str__(self):
        return f"========\ninst fetch from {_safe_format(self.addr)}: {_safe_format(self.data)} ({disasm_inst(self.data) if self.data is not None else ""})"

class SimEventCpuStatus(SimEventBase):
    def __init__(self, pc:int, sp:int, r0:int, r1:int, inten:bool):
        self.pc = pc
        self.sp = sp
        self.r0 = r0
        self.r1 = r1
        self.inten = inten
    def __str__(self):
        return f"""
            $PC     $SP     $R0     $R1     INTEN
            ======  ======  ======  ======  ======
            {_safe_format(self.pc)}  {_safe_format(self.sp)}  {_safe_format(self.r0)}  {_safe_format(self.r1)}  {self.inten}
        """


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
        self.events.append(SimEventRegUpdate("$pc", self.pc, data))
        self.pc = data

    def _set_sp(self, data: int) -> None:
        self.events.append(SimEventRegUpdate("$sp", self.sp, data))
        self.sp = data

    def _set_r0(self, data: int) -> None:
        self.events.append(SimEventRegUpdate("$r0", self.r0, data))
        self.r0 = data

    def _set_r1(self, data: int) -> None:
        self.events.append(SimEventRegUpdate("$r1", self.r1, data))
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
                self._write_mem(0, new_pc)
                yield from self.wait_clk()
                self._set_pc(new_pc)
                yield from self.wait_clk()
                self.in_reset = False
            else:
                inst = self._read_mem(self.pc)
                self.events.append(SimEventInstFetch(self.pc, inst))
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
                noskip = True
                skip_pc_update = False
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
                elif inst_field_opcode == INST_UNK:
                    alu_result = alu_opa # this is an unused instruction code, but I don't want the simulator to blow up if it encounters it
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
                    # If we update $pc here, we should not update pc in the next step.
                    # NOTE: none of the predicates that can clear 'noskip' update $pc,
                    #       so we're fine completely skipping that step
                    skip_pc_update = inst_field_opa == OPA_PC
                yield from self.wait_clk()
                # Update PC
                if not skip_pc_update:
                    self._set_pc(self.pc + (1 if noskip else 2))
                # Update inten
                if inst_field_opcode == INST_SWAP and inst_field_d == 0:
                    self.inten = not self.inten
                self.events.append(SimEventCpuStatus(self.pc, self.sp, self.r0, self.r1, self.inten))
                yield from self.wait_clk()
    def terminate(self) -> Sequence[SimEventBase]:
        return (SimEventCpuStatus(self.pc, self.sp, self.r0, self.r1, self.inten),)

TERMINATE_ADDR = 0xffff
class System(object):
    def __init__(self):
        self.clock_consumers = set()
        self.generators: Set[Generator] = set()
        self.mem = Memory(16384, self) # We have 16k of core memory
        self.term = Terminator(self)
        self.bus = Bus(self)
        self.bus.register(0, self.mem)
        self.bus.register(TERMINATE_ADDR, self.term)
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
        self.terminated = False
        self.generators.clear()
        for consumer in self.clock_consumers:
            self.generators.add(consumer.simulate())
        for clk in range(clock_count+1):
            events = []
            for generator in self.generators:
                events += generator.send(None)
            #print(f"======= CLK {clk} =========")
            for event in events:
                print("    " + str(event))
            for event in events:
                event.act(self)
            if self.terminated: break

    def terminate(self):
        events = []
        events += self.cpu.terminate()
        events += self.bus.terminate()
        print("********************************")
        for event in events:
            print("    " + str(event))
        self.terminated = True


if __name__ == "__main__":
    sim = System()
    sim.load(0, (0x1000,)) # reset vector
    sim.load_asm(
"""
    ; Simple test for all instruction formats and addressing modes
    .section TEXT 0x1000
    MOV $sp, 1
    MOV $r0, 3
    mov $r1, 2
    mov [$sp], $sp    ; should write to address 1
    mov [$r0-1], $r0  ; should write to address 2
    mov [$sp+2], $r1  ; should write to address 3
    xor $r0, $r0
    mov [-1], $r0
    mov $pc, $pc
"""
    )
    sim.simulate(50)
