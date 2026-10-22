#!/usr/bin/python3
# Runs a binary image on the RTL CPU model, starting at address 0.
#
# Usage: tb_fetch_av.py <image.bin>
#
# The image is a little-endian dump of 16-bit words (objcopy -O binary
# output). The run ends when the program writes the termination port of
# tb_cpu.py (0xffe0), whose value is printed as the exit code. See av.s for
# the MMU access violation tests. Writes tb_fetch_av.vcd in the current
# directory.

import sys
from silicon import *
import tb_cpu
from tb_cpu import Memory, Cpu, DataType, AddrType

class TB(Module):
    clk = ClkPort()
    bus_d_rd = Output(DataType)
    bus_d_wr = Output(DataType)
    bus_a = Output(AddrType)
    bus_wr = Output(logic)
    bus_rd = Output(logic)
    rst = RstPort(logic)
    interrupt = Output(logic)

    def body(self):
        dut = Cpu()
        self.bus_wr <<= dut.bus_wr
        self.bus_rd <<= dut.bus_rd
        self.bus_a <<= dut.bus_a
        self.bus_d_wr <<= dut.bus_d_out
        dut.bus_d_in <<= self.bus_d_rd
        dut.interrupts <<= concat("6'b0", self.interrupt)
        self.mem = Memory(64*1024)
        self.mem.bus_a <<= self.bus_a
        self.mem.bus_d_wr <<= self.bus_d_wr
        self.mem.bus_wr <<= self.bus_wr
        self.mem.bus_rd <<= self.bus_rd
        self.mem.inst_load <<= dut.inst_load
        self.bus_d_rd <<= self.mem.bus_d_rd

    def simulate(self):
        data = open(sys.argv[1], "rb").read()
        self.mem.load(0, [data[i] | data[i+1] << 8 for i in range(0, len(data), 2)])
        def clk():
            yield 5
            self.clk <<= ~self.clk & self.clk
            yield 5
            self.clk <<= ~self.clk
            yield 0
        self.interrupt <<= 0
        self.clk <<= 0
        self.rst <<= 1
        for i in range(15): yield from clk()
        self.rst <<= 0
        for i in range(3000):
            if tb_cpu.termination_code is not None:
                print(f"SIMULATION TERMINATED WITH EXIT CODE: 0x{tb_cpu.termination_code:04x}")
                return
            yield from clk()
        print("SIMULATION TIMED OUT")

if __name__ == "__main__":
    Build.simulation(lambda: TB(), "tb_fetch_av.vcd", add_unnamed_scopes=True)
