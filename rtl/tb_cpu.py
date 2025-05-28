#!/usr/bin/python3
from typing import *
from silicon import *

from cpu import *
from asm import *

class Memory(GenericModule):
    clk = ClkPort()
    bus_d_rd = Output(DataType)
    bus_d_wr = Input(DataType)
    bus_a = Input(AddrType)
    bus_cmd = Input(EnumNet(BusCmds))

    def construct(self, size: int, base_addr: int = 0):
        self.mem = {}
        self.size = size
        self.base_addr = base_addr

    def simulate(self):
        while(True):
            now = yield (self.bus_cmd, self.bus_a, self.bus_d_wr, self.clk)
            if (self.bus_cmd.sim_value is None):
                continue
            if (self.bus_cmd == BusCmds.read):
                if self.bus_a.sim_value is None:
                    print(f"{now}: Reading from NONE - ignored for now")
                    self.bus_d_rd <<= None
                    continue
                addr = int(self.bus_a.sim_value)
                data = self.mem.get(addr, None)
                if data is not None:
                    print(f"{now}: Reading MEM[0x{addr:04x}] -> 0x{data:04x}")
                else:
                    print(f"{now}: Reading MEM[0x{addr:04x}] -> NONE")
                self.bus_d_rd <<= data
                # Read is destructive, make sure we set the data to all 0-s
                if (self.clk == 0):
                    print(f"{now}: Resetting MEM[0x{addr:04x}] -> 0")
                    self.mem[addr] = 0
            elif ((self.bus_cmd == BusCmds.write) & (self.clk == 0)):
                if self.bus_a.sim_value is None:
                    print(f"{now}: Writing to NONE - ignored for now")
                    continue
                addr = int(self.bus_a.sim_value)
                data = self.bus_d_wr.sim_value
                if data is not None:
                    data &= 0xffff
                    print(f"{now}: Writing MEM[0x{addr:04x}] = 0x{data:04x}")
                else:
                    print(f"{now}: Writing MEM[0x{addr:04x}] = NONE")
                # Write can only flip bits from 0 to 1. So, we have to make sure that all writes happen to locations
                # that have been reset to 0 by a read previously
                assert self.mem[addr] == 0
                self.mem[addr] = data
            else:
                self.bus_d_rd <<= None
    def set(self, addr, data):
        self.mem[addr] = data & 0xffff if data is not None else None
    def get(self, addr):
        return self.mem.get(addr, None)

    def get_size(self) -> int:
        return self.size

    def load(self, start_addr: int, content: Sequence[int]) -> None:
        assert start_addr >= self.base_addr
        assert start_addr < self.base_addr + self.size
        for ofs, data in enumerate(content):
            assert ofs + start_addr < self.base_addr + self.size
            self.mem[ofs+start_addr] = data

    def compare(self, expected_content: Dict[int, Sequence[int]]) -> bool:
        checked_addresses: Set[int] = set()
        ret_val = True
        for start, values in expected_content.items():
            for ofs, value in enumerate(values):
                addr = start+ofs
                if addr not in self.mem:
                    print(f"Expected content at address 0x{addr:04x} with value 0x{value:04x} is deleted from memory")
                    ret_val = False
                elif self.mem[addr] != value:
                    print(f"Expected content at address 0x{addr:04x} with expected value 0x{value:04x} is different in memory with value: 0x{self.mem[addr]:04x}")
                    ret_val = False
                checked_addresses.add(addr)
        for addr in self.mem.keys():
            if addr not in checked_addresses:
                print(f"Memory contains extraneous data at address 0x{addr:04x} with value: 0x{self.mem[addr]:04x}")
                ret_val = False
        return ret_val








bct_code = \
"""
    ; This is a basic confidence test
    ; We start by not assuming anything works
    ; and build our toolbox as we go.
    ; During the test we save things into memory
    ; and rely on post-execution memory content compare
    ; to verify that things went well. At least for the very
    ; beginning.
    .section TEXT 0x1000
    .def TERMINATE_PORT = -1
    MOV $sp, 3
    mov [1], $sp      ; we should expect memory location 1 to contain 3
    mov $r0, 4
    mov [$sp-1], $r0  ; we should expect memory location 2 to contain 4
    mov $r1, 5
    sub $sp, 1
    mov [$sp+1], $r1  ; we should expect memory location 3 to contain 5
    add $sp, 4
    mov [$r0], $sp   ; we should expect memory location 4 to contain 6
    ; At this point we can trust loading constants into registers
    ; and memory writes with offsets to work at least $sp-relative and immediate
    ; we can also trust add and subtract to a certain degree
    ; From here on, we put counter in $r1 and we're going to decrement it every time we test something
    ; Eventually we declare success by terminating with code 0
    mov $r1, 31
    add $r1, 31
    if_eq $r0, $sp
    mov [TERMINATE_PORT], $r1     ; This we should skip
    if_neq $r0, 4
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    sub $r1, 1
    if_eq $r0, 4
    mov $pc, $pc+2                   ; This we should NOT skip
    mov [TERMINATE_PORT], $r1
    if_neq $r0, 3
    mov $pc, $pc+2                   ; This we should NOT skip
    mov [TERMINATE_PORT], $r1
    sub $r1, 1

    ; Now we can trust equal and not-equal compares, so let's do some arithmetic!
    mov $r0, 31
    mov $sp, $r0
    rol $r0
    isub $r0, $sp     ; $r0 should contain 31-62 = -31
    isub $sp, 0
    if_neq $sp, $r0
    mov [TERMINATE_PORT], $r1    ; This we should skip
    sub $r1, 1
    mov $r0, 3
    ror $r0
    if_neq $r0, $r0 ; skip over a constant
    .word 0b1000_0000_0000_0001
    if_neq $r0, [$pc-1] ; reference the constant above
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    ; Now we trust ADD,SUB,ISUB, ROL,ROR,MOV, at least on a basic level
    sub $r1, 1
    mov $sp, 12
    mov $r0, 26
    xor $r0, $sp
    if_neq $r0, (12 ^ 26)
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $r0, 26
    and $r0, $sp
    if_neq $r0, (12 & 26)
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $r0, 26
    or $r0, $sp
    if_neq $r0, (12 | 26)
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    sub $r1, 1
    ; Now we trust AND,OR,XOR,ADD,SUB,ISUB, ROL,ROR,MOV, at least on a basic level
    ; We will play around with ISTAT and SWAP (as well as SWAPI)
    ; We don't actually have interrupts implemented, but we can test the interrupt enable behavior
    istat $r0
    if_neq $r0, 0
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $sp, 7
    mov $r0, 0x10
    mov [5], $r0
    add $r0, 1
    swap $sp, [5]
    if_neq $sp, 0x10
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    istat $r0
    if_neq $r0, 0
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $r0, 0x11
    mov $sp, 5
    swapi $r0, [$sp]
    if_neq $r0, 0x7
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $r0, [$sp]
    if_neq $r0, 0x11
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    istat $r0
    if_neq $r0, 2
    mov [TERMINATE_PORT], $r1    ; This we should skip too

    mov $r0, 7
    sub $sp, 1
    swapi $r0, [$sp+1]
    if_neq $r0, 0x11
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $sp, [$sp+1]
    if_neq $sp, 7
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    istat $r0
    if_neq $r0, 0
    mov [TERMINATE_PORT], $r1    ; This we should skip too

    ; At this point we trust all instructions, except for a few predicates. Let's test those...
    mov $sp, 3
    mov $r0, 5
    if_ltu $r0, $sp
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $r0, -4
    if_lts $sp, $r0
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $sp, -4
    if_lts $sp, $r0
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $sp, 3
    if_les $sp, $r0
    mov [TERMINATE_PORT], $r1    ; This we should skip too

    if_geu $sp, $r0
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $r0, -4
    if_ges $r0, $sp
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $sp, -4
    if_ges $r0, $sp
    mov $pc, $pc+2
    mov [TERMINATE_PORT], $r1    ; This we should skip too
    mov $sp, 3
    if_gts $r0, $sp
    mov [TERMINATE_PORT], $r1    ; This we should skip too

    ; Now let's test the inverse cases to make sure we indeed have conditionals
    mov $sp, 3
    mov $r0, 5
    if_ltu $sp, $r0
    mov $pc, $pc+2
    mov [TERMINATE_PORT], $r1
    mov $r0, -4
    if_lts $r0, $sp
    mov $pc, $pc+2
    mov [TERMINATE_PORT], $r1
    mov $sp, 3
    if_les $r0, $sp
    mov $pc, $pc+2
    mov [TERMINATE_PORT], $r1

    if_geu $r0, $sp
    mov $pc, $pc+2
    mov [TERMINATE_PORT], $r1
    mov $r0, -4
    if_ges $r0, $r0
    mov $pc, $pc+2
    mov [TERMINATE_PORT], $r1
    mov $sp, 3
    if_gts $sp, $r0
    add $pc, 2
    mov [TERMINATE_PORT], $r1

    ; During these tests, we also had a bunch of PC manipulation instructions.
    ; That is to say: we've tested the fact that PC should not get incremented
    ; if it was the target of the operation. So, at this point, we can be pretty
    ; confident in our ISA implementation. There still could be edge-cases of
    ; course and this is not a full test, but should suffice as a basic confidence
    ; test.
    ; As an added insurance we're going to test the memory content for extraneous
    ; writes or corruption in expected values. But that step is outside the CPU.

    mov $r1, 0
    mov [TERMINATE_PORT], $r1    ; WE DECLARE SUCCESS HERE!
    mov $pc, $pc
"""




class TB(Module):
    clk = ClkPort()
    bus_d_rd = Output(DataType)
    bus_d_wr = Output(DataType)
    bus_a = Output(AddrType)
    bus_cmd = Output(EnumNet(BusCmds))
    rst = RstPort(logic)
    interrupt = Output(logic)

    def body(self):
        dut = Cpu()
        self.bus_cmd <<= dut.bus_cmd
        self.bus_a <<= dut.bus_a
        self.bus_d_wr <<= dut.bus_d_out
        dut.bus_d_in <<= self.bus_d_rd

        dut.interrupt <<= self.interrupt

        self.mem = Memory(16*1024)
        self.mem.bus_a <<= self.bus_a
        self.mem.bus_d_wr <<= self.bus_d_wr
        self.mem.bus_cmd <<= self.bus_cmd
        self.bus_d_rd <<= self.mem.bus_d_rd

    def simulate(self):
        self.mem.set(0, 0x1000) # Reset vector to 0x1000
        base_addr, words = assemble(bct_code)
        self.mem.load(base_addr, words)


        #self.mem.set(0x1000, (INST_MOV   << 12) | (DEST_REG << 11)    | (OPB_IMMED        << 8) | (OPA_SP << 6) | (3 << 0))
        #self.mem.set(0x1001, (INST_MOV   << 12) | (DEST_REG << 11)    | (OPB_IMMED        << 8) | (OPA_R0 << 6) | (4 << 0))
        #self.mem.set(0x1002, (INST_MOV   << 12) | (DEST_REG << 11)    | (OPB_IMMED        << 8) | (OPA_R1 << 6) | (0x3f << 0))
        #self.mem.set(0x1003, (INST_ADD   << 12) | (DEST_REG << 11)    | (OPB_IMMED        << 8) | (OPA_SP << 6) | (1 << 0))
        #self.mem.set(0x1004, (INST_EQ    << 12) | (PRED_INVERT << 11) | (OPB_IMMED        << 8) | (OPA_SP << 6) | (3 << 0))
        #self.mem.set(0x1005, (INST_MOV   << 12) | (DEST_REG << 11)    | (OPB_MEM_IMMED_PC << 8) | (OPA_PC << 6) | (2 << 0))
        #self.mem.set(0x1006, (INST_MOV   << 12) | (DEST_REG << 11)    | (OPB_IMMED_PC     << 8) | (OPA_PC << 6) | (0 << 0))
        #self.mem.set(0x1007, 0x1005) # Endless loop


        def clk():
            yield 5
            self.clk <<= ~self.clk & self.clk
            yield 5
            self.clk <<= ~self.clk
            yield 0

        self.clk <<= 0
        self.rst <<= 1
        self.interrupt <<= 0
        for i in range(15): yield from clk()
        self.rst <<= 0
        for i in range(5000): yield from clk()

def sim():
    def sim_top():
        return TB()

    Build.simulation(sim_top, "tb_cpu.vcd", add_unnamed_scopes=True)

if __name__ == "__main__":
    sim()

