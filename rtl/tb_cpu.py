#!/usr/bin/python3
from typing import *
from silicon import *

from cpu import *

class Memory(Module):
    clk = ClkPort()
    bus_d_rd = Output(DataType)
    bus_d_wr = Input(DataType)
    bus_a = Input(AddrType)
    bus_cmd = Input(EnumNet(BusCmds))

    content = {}
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
                data = self.content.get(addr, None)
                if data is not None:
                    print(f"{now}: Reading MEM[0x{addr:04x}] -> 0x{data:04x}")
                else:
                    print(f"{now}: Reading MEM[0x{addr:04x}] -> NONE")
                self.bus_d_rd <<= data
                # Read is destructive, make sure we set the data to all 0-s
                if (self.clk == 0):
                    print(f"{now}: Resetting MEM[0x{addr:04x}] -> 0")
                    self.content[addr] = 0
            elif ((self.bus_cmd == BusCmds.write) & (self.clk == 0)):
                if self.bus_a.sim_value is None:
                    print(f"{now}: Writing to NONE - ignored for now")
                    continue
                addr = int(self.bus_a.sim_value)
                data = self.bus_d_wr.sim_value
                if data is not None:
                    print(f"{now}: Writing MEM[0x{addr:04x}] = 0x{data:04x}")
                else:
                    print(f"{now}: Writing MEM[0x{addr:04x}] = NONE")
                # Write can only flip bits from 0 to 1. So, we have to make sure that all writes happen to locations
                # that have been reset to 0 by a read previously
                assert self.content[addr] == 0
                self.content[addr] = data
            else:
                self.bus_d_rd <<= None
    def set(self, addr, data):
        self.content[addr] = data
    def get(self, addr):
        return self.content.get(addr, None)

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

        self.mem = Memory()
        self.mem.bus_a <<= self.bus_a
        self.mem.bus_d_wr <<= self.bus_d_wr
        self.mem.bus_cmd <<= self.bus_cmd
        self.bus_d_rd <<= self.mem.bus_d_rd

    def simulate(self):
        self.mem.set(0, 0x1000) # Reset vector to 0x1000
        self.mem.set(0x1000, (INST_MOV   << 12) | (DEST_REG << 11) | (OPB_IMMED        << 8) | (OPA_SP << 6) | (3 << 0))
        self.mem.set(0x1001, (INST_MOV   << 12) | (DEST_REG << 11) | (OPB_IMMED        << 8) | (OPA_R0 << 6) | (4 << 0))
        self.mem.set(0x1002, (INST_MOV   << 12) | (DEST_REG << 11) | (OPB_IMMED        << 8) | (OPA_R1 << 6) | (0x3f << 0))
        self.mem.set(0x1003, (INST_ADD   << 12) | (DEST_REG << 11) | (OPB_IMMED        << 8) | (OPA_SP << 6) | (1 << 0))
        self.mem.set(0x1004, (INST_MOV   << 12) | (DEST_REG << 11) | (OPB_MEM_IMMED_PC << 8) | (OPA_PC << 6) | (1 << 0))
        self.mem.set(0x1005, 0x1004) # Endless loop

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
        for i in range(50): yield from clk()

def sim():
    def sim_top():
        return TB()

    Build.simulation(sim_top, "tb_cpu.vcd", add_unnamed_scopes=True)

if __name__ == "__main__":
    sim()

