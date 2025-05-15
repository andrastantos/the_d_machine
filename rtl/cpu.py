#!/usr/bin/python3
from typing import *
from silicon import *
from silicon.memory import SimpleDualPortMemory
#sys.path.append(str(Path(__file__).parent))

from .brew_types import *

"""
This is a simulation model of the transistorized computer.

It is intended to verify the design concepts and serve as a reference implementation.
Since Silicon (at least at the moment) doesn't output netlists and at any rate optimizing
the logic to transistors is a significant undertaking, right now this is NOT the design
that is the basis of the physical implementation.
"""

AddrType = Unsigned(16)
DataType = Unsigned(16)

class BusCmds(Enum):
    idle                 = 0
    read                 = 1
    write                = 2

class AluCmds(Enum):
    alu_add                 = 0
    alu_sub                 = 1
    alu_or                  = 2
    alu_and                 = 3
    alu_xor                 = 4
    alu_ror                 = 5
    alu_rol                 = 6

class LBusDSelect(Enum):
    bus_d = 0
    alu_result = 1

class AluASelect(Enum):
    pc = 0
    sp = 1
    r0 = 2
    r1 = 3
    zero = 4
    int_stat = 5

class AluBSelect(Enum):
    immed = 0
    zero = 1
    l_bus_d = 2

# Values for instruction fields
OPA_PC = 0b00
OPA_SP = 0b01
OPA_R0 = 0b10
OPA_R1 = 0b11

OPB_IMMED_PC =     0b000
OPB_IMMED_SP =     0b001
OPB_IMMED_R0 =     0b010
OPB_IMMED =        0b011
OPB_MEM_IMMED_PC = 0b100
OPB_MEM_IMMED_SP = 0b101
OPB_MEM_IMMED_R0 = 0b110
OPB_MEM_IMMED_R1 = 0b111

INST_SWAP = 0b0000
INST_MOV  = 0b0001
INST_ADD  = 0b0010
INST_SUB  = 0b0011
INST_NOR  = 0b0100
INST_NAND = 0b0101
INST_XOR  = 0b0110

class ALU(Module):
    a_in = Input(DataType)
    b_in = Input(DataType)
    cmd_in = Input(EnumNet(AluCmds))
    c_in = Input(logic)

    o_out = Output(DataType)
    c_out = Output(logic)
    z_out = Output(logic)
    s_out = Output(logic)

    def body(self):
        full_add = self.a_in + Select(self.cmd_in == AluCmds.alu_sub, self.b_in, ~self.b_in) + self.c_in
        result = SelectOne(
            self.cmd_in == AluCmds.alu_add, full_add[15:0],
            self.cmd_in == AluCmds.alu_sub, full_add[15:0],
            self.cmd_in == AluCmds.alu_or, self.a_in | self.b_in,
            self.cmd_in == AluCmds.alu_and, self.a_in & self.b_in,
            self.cmd_in == AluCmds.alu_xor, self.a_in ^ self.b_in,
            self.cmd_in == AluCmds.alu_ror, {self.a_in[15], self.a_in[14:0]},
            self.cmd_in == AluCmds.alu_xor, {self.a_in[14:0], self.a_in[15]},
        )
        self.a_out = result
        self.c_out = full_add[16]
        self.z_out = result == 0
        self.s_out = result[15]

class DataPath(Module):
    rst = Input(logic)
    interrupt = Input(logic)

    bus_d_out = Output(DataType)
    bus_d_in = Input(DataType)
    bus_a = Output(DataType)

    l_bus_a_ld = Input(logic)
    l_bus_d_ld = Input(logic)
    l_alu_result_ld = Input(logic)
    l_pc_ld = Input(logic)
    l_sp_ld = Input(logic)
    l_r0_ld = Input(logic)
    l_r1_ld = Input(logic)
    l_inst_ld = Input(logic)

    l_bus_d_select = Input(EnumNet(LBusDSelect))
    alu_a_select = Input(EnumNet(AluASelect))
    alu_b_select = Input(EnumNet(AluBSelect))
    alu_cmd = Input(EnumNet(AluCmds))

    inhibit = Input(logic)
    intdis = Input(logic)

    alu_c_in = Input(logic)
    alu_c_out = Output(logic)
    alu_z_out = Output(logic)
    alu_s_out = Output(logic)

    inst_field_opcode = Output(Unsigned(5))
    inst_field_opb = Output(Unsigned(3))
    inst_field_opa = Output(Unsigned(2))

    def body(self):
        # The 8 latches we have in our system
        l_bus_a = LowLatch()
        l_bus_d = LowLatch()
        l_alu_result = LowLatch()
        l_pc = LowLatch()
        l_sp = LowLatch()
        l_r0 = LowLatch()
        l_r1 = LowLatch()
        l_inst = LowLatch()

        alu_a_in = Wire()
        alu_b_in = Wire()
        alu_result = Wire()

        immed = Unsigned(16)
        # Sign-extend the immediate field to 16 bits
        immed <<= {
            l_inst[5], l_inst[5], l_inst[5], l_inst[5],
            l_inst[5], l_inst[5], l_inst[5], l_inst[5],
            l_inst[5], l_inst[5], l_inst[5:0]
        }
        self.inst_field_opcode = l_inst[15:11]
        self.inst_field_opb = l_inst[10:8]
        self.inst_field_opa = l_inst[7:6]

        alu = ALU()
        alu_result <<= alu.o_out
        self.alu_c_out <<= alu.c_out
        self.alu_z_out <<= alu.z_out
        self.alu_s_out <<= alu.s_out
        alu.a_in <<= alu_a_in
        alu.b_in <<= alu_b_in
        alu.cmd_in <<= self.alu_cmd
        alu.c_in <<= self.alu_c_in

        l_bus_a.latch_port <<= self.l_bus_a_ld
        l_bus_d.latch_port <<= self.l_bus_d_ld
        l_alu_result.latch_port <<= self.l_alu_result_ld
        l_pc.latch_port <<= self.l_pc_ld
        l_sp.latch_port <<= self.l_sp_ld
        l_r0.latch_port <<= self.l_r0_ld
        l_r1.latch_port <<= self.l_r1_ld
        l_inst.latch_port <<= self.l_inst_ld

        l_bus_a.input_port <<= alu_result
        l_bus_d.input_port <<= SelectOne(
            self.l_bus_d_select == LBusDSelect.bus_d, self.bus_d_in,
            self.l_bus_d_select == LBusDSelect.alu_result, alu_result
        )
        l_alu_result.input_port <<= alu_result
        l_pc.input_port <<= l_alu_result.output_port
        l_sp.input_port <<= l_alu_result.output_port
        l_r0.input_port <<= l_alu_result.output_port
        l_r1.input_port <<= l_alu_result.output_port

        l_inst.input_port <<= SelectFirst(
            self.inhibit == 1, 0b0_100_0_011_00_000000,
            (self.intdis == 0) & (self.interrupt | self.rst), 0b0_000_0_000_00_000000,
            self.bus_d_in
        )

        alu_a_in = SelectOne(
            self.alu_a_select == AluASelect.pc, l_pc.output_port,
            self.alu_a_select == AluASelect.sp, l_sp.output_port,
            self.alu_a_select == AluASelect.r0, l_r0.output_port,
            self.alu_a_select == AluASelect.r1, l_r1.output_port,
            self.alu_a_select == AluASelect.zero, 0,
            self.alu_a_select == AluASelect.int_stat, {self.intdis, self.interrupt}
        )
        alu_b_in = SelectOne(
            self.alu_b_select == AluBSelect.immed, immed,
            self.alu_b_select == AluBSelect.zero, 0,
            self.alu_b_select == AluBSelect.l_bus_d, l_bus_d.output_port
        )


class Sequencer(Module):
    clk = ClkInput()
    rst = RstInput()

    interrupt = Input(logic)

    bus_cmd = Output(EnumNet(BusCmds))

    l_bus_a_ld =      Output(logic)
    l_bus_d_ld =      Output(logic)
    l_alu_result_ld = Output(logic)
    l_pc_ld =         Output(logic)
    l_sp_ld =         Output(logic)
    l_r0_ld =         Output(logic)
    l_r1_ld =         Output(logic)
    l_inst_ld =       Output(logic)

    l_bus_d_select = Output(EnumNet(LBusDSelect))
    alu_a_select =   Output(EnumNet(AluASelect))
    alu_b_select =   Output(EnumNet(AluBSelect))
    alu_cmd =        Output(EnumNet(AluCmds))

    inhibit = Output(logic)
    intdis =  Output(logic)

    alu_c_in =  Output(logic)
    alu_c_out = Input(logic)
    alu_z_out = Input(logic)
    alu_s_out = Input(logic)

    inst_field_opcode = Input(Unsigned(5))
    inst_field_opb    = Input(Unsigned(3))
    inst_field_opa    = Input(Unsigned(2))

    def body(self):
        # State
        update_reg = Wire(logic)
        update_mem = Wire(logic)
        l_inhibit = Wire(logic)
        l_intdis = Wire(logic)

        phase = Wire(Number(low=0,high=4))

        phase <<= Select(self.rst, Select(phase == 4, phase + 1, 0), 0)

        self.bus_cmd <<= Select(phase,
            BusCmds.read,
            BusCmds.write,
            BusCmds.read,
            BusCmds.write,
            Select(update_mem, BusCmds.idle, BusCmds.write),
        )

        self.l_bus_a_ld <<= Select(phase,
            1,
            0,
            1,
            0,
            0,
        )

        self.l_bus_d_ld <<= Select(phase,
            1,
            0,
            1,
            0,
            1,
        )

        self.l_bus_d_select <<= Select(phase,
            LBusDSelect.bus_d,
            LBusDSelect.bus_d,
            LBusDSelect.bus_d,
            LBusDSelect.bus_d,
            LBusDSelect.alu_result,
        )

        self.l_alu_result_ld <<= Select(phase,
            1,
            0,
            0,
            1,
            0,
        )

        self.l_pc_ld <<= Select(phase,
            0,
            1,
            0,
            0,
            update_reg & (self.inst_field_opa == OPA_PC),
        )