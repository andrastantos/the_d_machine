#!/usr/bin/python3
from typing import *
from silicon import *

from cpu import *

class Memory(Module):
    bus_d_rd = Output(DataType)
    bus_d_wr = Input(DataType)
    bus_a = Input(AddrType)
    bus_cmd = Input(EnumNet(BusCmds))

    content = {}
    def simulate(self):
        while(True):
            yield (self.bus_cmd, self.bus_a, self.bus_d_wr)
            if (self.bus_cmd == BusCmds.read):
                if self.bus_a.sim_value is None:
                    print("Reading from NONE - ignored for now")
                    self.bus_d_rd <<= None
                    return
                addr = int(self.bus_a.sim_value)
                data = self.content.get(addr, None)
                if data is not None:
                    print(f"Reading MEM[0x{addr:04x}] -> 0x{data:04x}")
                else:
                    print(f"Reading MEM[0x{addr:04x}] -> NONE")
                self.bus_d_rd <<= data
            elif (self.bus_cmd == BusCmds.write):
                if self.bus_a.sim_value is None:
                    print("Writing to NONE - ignored for now")
                    return
                addr = int(self.bus_a.sim_value)
                data = self.bus_d_wr.sim_value
                if data is not None:
                    print(f"Writing MEM[0x{addr:04x}] = 0x{data:04x}")
                else:
                    print(f"Writing MEM[0x{addr:04x}] = NONE")
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

    def body(self):
        dut = Cpu()
        self.bus_cmd <<= dut.bus_cmd
        self.bus_a <<= dut.bus_a
        self.bus_d_wr <<= dut.bus_d_out
        dut.bus_d_in <<= self.bus_d_rd

        self.mem = Memory()
        self.mem.bus_a <<= self.bus_a
        self.mem.bus_d_wr <<= self.bus_d_wr
        self.mem.bus_cmd <<= self.bus_cmd
        self.bus_d_rd <<= self.mem.bus_d_rd

    def simulate(self):
        self.mem.set(0, 0x1000) # Reset vector to 0x1000
        self.mem.set(0x1000, (INST_MOV   << 12) | (DEST_REG << 11) | (OPB_IMMED        << 8) | (OPA_SP << 6) | (0 << 0))
        self.mem.set(0x1001, (INST_MOV   << 12) | (DEST_REG << 11) | (OPB_IMMED        << 8) | (OPA_R0 << 6) | (0 << 0))
        self.mem.set(0x1002, (INST_MOV   << 12) | (DEST_REG << 11) | (OPB_IMMED        << 8) | (OPA_R1 << 6) | (0 << 0))
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
        for i in range(15): yield from clk()
        self.rst <<= 0
        for i in range(50): yield from clk()

def sim():
    def sim_top():
        return TB()

    Build.simulation(sim_top, "tb_cpu.vcd", add_unnamed_scopes=True)

if __name__ == "__main__":
    sim()

