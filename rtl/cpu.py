#!/usr/bin/python3
from typing import *
from silicon import *
from silicon.memory import SimpleDualPortMemory
from constants import *

"""
This is a simulation model of the transistorized computer.

It is intended to verify the design concepts and serve as a reference implementation.
Since Silicon (at least at the moment) doesn't output netlists and at any rate optimizing
the logic to transistors is a significant undertaking, right now this is NOT the design
that is the basis of the physical implementation.
"""

AddrType = Unsigned(16)
DataType = Unsigned(16)



class ALU(Module):
    a_in = Input(DataType)
    b_in = Input(DataType)
    cmd_in = Input(EnumNet(AluCmds))
    inv_a_in = Input(logic)
    inv_b_in = Input(logic)
    c_in = Input(logic)

    o_out = Output(DataType)
    c_out = Output(logic)
    z_out = Output(logic)
    s_out = Output(logic)
    v_out = Output(logic)

    def body(self):
        a_in = self.a_in ^ concat(self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in, self.inv_a_in)
        b_in = self.b_in ^ concat(self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in, self.inv_b_in)
        full_add = a_in + b_in + self.c_in
        result = SelectOne(
            self.cmd_in == AluCmds.alu_add, full_add[15:0],
            self.cmd_in == AluCmds.alu_nor, (a_in | b_in) ^ 0xffff,
            self.cmd_in == AluCmds.alu_nand, (a_in & b_in) ^ 0xffff,
            self.cmd_in == AluCmds.alu_xor, a_in ^ b_in,
            self.cmd_in == AluCmds.alu_ror, concat(a_in[0], a_in[15:1]),
            self.cmd_in == AluCmds.alu_rol, concat(a_in[14:0], a_in[15]),
        )
        self.o_out <<= result
        self.c_out <<= full_add[16] ^ (self.inv_a_in | self.inv_b_in)
        self.z_out <<= result == 0
        self.s_out <<= result[15]
        # overflow for now is only valid for a_minus_b (which is what all the predicates use)
        # See https://en.wikipedia.org/wiki/Overflow_flag for details
        minuend_msb = self.a_in[15] #Select(self.inv_b_in, self.b_in[15], self.a_in[15])
        self.v_out <<= (self.a_in[15] != self.b_in[15]) & (minuend_msb != result[15])


class DataPath(Module):
    clk = ClkPort()
    rst = RstPort()
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
    alu_inv_a_in = Input(logic)
    alu_inv_b_in = Input(logic)

    intdis = Input(logic)

    alu_c_in = Input(logic)
    alu_c_out = Output(logic)
    alu_z_out = Output(logic)
    alu_s_out = Output(logic)
    alu_v_out = Output(logic)

    inst_field_opcode = Output(Unsigned(4))
    inst_field_d   = Output(logic)
    inst_field_opb = Output(Unsigned(3))
    inst_field_opa = Output(Unsigned(2))

    def body(self):
        # The 8 latches we have in our system
        l_bus_a = HighLatch()
        l_bus_d = HighLatch()
        l_alu_result = HighLatch()
        l_pc = HighLatch()
        l_sp = HighLatch()
        l_r0 = HighLatch()
        l_r1 = HighLatch()
        l_inst = HighLatch()
        inst = Wire(DataType)

        alu_a_in = Wire()
        alu_b_in = Wire()
        alu_result = Wire()

        inst <<= l_inst.output_port
        immed = Wire(Unsigned(16))
        # Sign-extend the immediate field to 16 bits
        immed_sign = inst[IMMED_OFS+IMMED_SIZE-1]
        immed <<= concat(
            immed_sign, immed_sign, immed_sign, immed_sign,
            immed_sign, immed_sign, immed_sign, immed_sign,
            immed_sign, immed_sign, inst[IMMED_OFS+IMMED_SIZE-1:IMMED_OFS]
        )
        self.inst_field_opcode <<= inst[OPCODE_OFS+OPCODE_SIZE-1:OPCODE_OFS]
        self.inst_field_d <<= inst[D_OFS+D_SIZE-1:D_OFS]
        self.inst_field_opb <<= inst[OPB_OFS+OPB_SIZE-1:OPB_OFS]
        self.inst_field_opa <<= inst[OPA_OFS+OPA_SIZE-1:OPA_OFS]

        alu = ALU()
        alu_result <<= alu.o_out
        self.alu_c_out <<= alu.c_out
        self.alu_z_out <<= alu.z_out
        self.alu_s_out <<= alu.s_out
        self.alu_v_out <<= alu.v_out
        alu.a_in <<= alu_a_in
        alu.b_in <<= alu_b_in
        alu.cmd_in <<= self.alu_cmd
        alu.inv_a_in <<= self.alu_inv_a_in
        alu.inv_b_in <<= self.alu_inv_b_in
        alu.c_in <<= self.alu_c_in

        l_bus_a.latch_port <<= self.l_bus_a_ld
        l_bus_d.latch_port <<= self.l_bus_d_ld
        l_alu_result.latch_port <<= self.l_alu_result_ld
        l_pc.latch_port <<= self.l_pc_ld
        l_sp.latch_port <<= self.l_sp_ld
        l_r0.latch_port <<= self.l_r0_ld
        l_r1.latch_port <<= self.l_r1_ld
        l_inst.latch_port <<= self.l_inst_ld | self.rst
        l_inst.reset_port <<= 0

        l_bus_a.input_port <<= alu_result
        l_bus_d.input_port <<= SelectOne(
            self.l_bus_d_select == LBusDSelect.bus_d, self.bus_d_in,
            self.l_bus_d_select == LBusDSelect.alu_result, alu_result,
            self.l_bus_d_select == LBusDSelect.l_alu_result, l_alu_result.output_port
        )
        l_alu_result.input_port <<= alu_result
        l_pc.input_port <<= l_alu_result.output_port
        l_sp.input_port <<= l_alu_result.output_port
        l_r0.input_port <<= l_alu_result.output_port
        l_r1.input_port <<= l_alu_result.output_port

        serve_interrupt = ((self.intdis == 0) & self.interrupt)

        l_inst.input_port <<= SelectFirst(
            serve_interrupt | self.rst, (Select(self.rst, INST_SWAP, INST_MOV) << OPCODE_OFS) | (DEST_REG << D_OFS) | (OPB_MEM_IMMED << OPB_OFS) | (OPA_PC << OPA_OFS) | ((~self.rst) << IMMED_OFS),
            default_port = self.bus_d_in
        )

        alu_a_in <<= SelectOne(
            self.alu_a_select == AluASelect.pc, l_pc.output_port,
            self.alu_a_select == AluASelect.sp, l_sp.output_port,
            self.alu_a_select == AluASelect.r0, l_r0.output_port,
            self.alu_a_select == AluASelect.r1, l_r1.output_port,
            self.alu_a_select == AluASelect.zero, 0,
            self.alu_a_select == AluASelect.int_stat, concat(self.intdis, self.interrupt),
            self.alu_a_select == AluASelect.l_bus_d, l_bus_d.output_port,
            #self.alu_a_select == AluASelect.l_bus_a, l_bus_a.output_port
        )
        alu_b_in <<= SelectOne(
            self.alu_b_select == AluBSelect.immed, immed,
            self.alu_b_select == AluBSelect.zero, 0,
            self.alu_b_select == AluBSelect.one, 1,
            self.alu_b_select == AluBSelect.l_bus_d, l_bus_d.output_port,
            self.alu_b_select == AluBSelect.l_bus_a, l_bus_a.output_port
        )

        self.bus_d_out <<= l_bus_d.output_port
        self.bus_a <<= l_bus_a.output_port

### TODO: there's a huge issue here!!! Any latch load signal with glitches is highly problematic!!!!
class Sequencer(Module):
    clk = ClkPort()
    rst = RstPort()

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
    alu_inv_a =      Output(logic)
    alu_inv_b =      Output(logic)

    intdis =  Output(logic)

    alu_c_in =  Output(logic)
    alu_c_out = Input(logic)
    alu_z_out = Input(logic)
    alu_s_out = Input(logic)
    alu_v_out = Input(logic)

    inst_field_opcode = Input(Unsigned(4))
    inst_field_d      = Input(logic)
    inst_field_opb    = Input(Unsigned(3))
    inst_field_opa    = Input(Unsigned(2))

    def body(self):
        # State
        update_reg = Wire(logic)
        update_mem = Wire(logic)
        l_skip = HighLatch()
        l_intdis_prev = HighLatch()
        l_intdis = HighLatch()
        l_was_branch = HighLatch()

        #phase = Wire(Number(min_val=0,max_val=5))
        phase = Wire(Unsigned(3))
        l_phase = HighLatch()
        l_phase_next = HighLatch()
        l_phase.latch_port <<= self.clk
        l_phase_next.latch_port <<= ~self.clk
        l_phase.input_port <<= l_phase_next.output_port
        l_phase.reset_value_port <<= 1
        l_phase_next.reset_value_port <<= 2
        phase <<= l_phase.output_port

        is_opb_mem_ref = self.inst_field_opb[2] != OPB_CLASS_IMM
        # We skip over phase 4 for anything but a SWAP instruction
        l_phase_next.input_port <<= Select(
            phase == 5,
            (phase + Select((self.inst_field_opcode == INST_SWAP) | (phase != 2), 2, 1))[2:0],
            0
        )

        update_mem <<= Select(
            self.inst_field_opcode == INST_SWAP,
            # Not a swap instruction
            Select(
                self.inst_field_opcode[3:2] == INST_GROUP_PREDICATE,
                # Not a predicate instruction --> field D determines if we write to memory
                (is_opb_mem_ref & self.inst_field_d),
                # predicate instructions never write to memory
                0
            ),
            # swap always writes to memory
            1
        )
        update_reg <<= Select(
            self.inst_field_opcode == INST_SWAP,
            # Not a swap instruction
            Select(
                self.inst_field_opcode[3:2] == INST_GROUP_PREDICATE,
                # Not a predicate instruction --> field D determines if we write to registers
                ~self.inst_field_d,
                # predicate instructions never write to registers
                0
            ),
            # swap always writes to registers
            1
        )

        self.bus_cmd <<= Select(self.rst,
            Select(phase,
                BusCmds.read,
                BusCmds.write,
                Select(is_opb_mem_ref, BusCmds.idle, BusCmds.read),
                BusCmds.idle, # SWAP-only cycle
                Select(is_opb_mem_ref & ~update_mem, BusCmds.idle, BusCmds.write),
                Select(update_mem, BusCmds.idle, BusCmds.write),
            ),
            BusCmds.idle
        )

        self.l_bus_a_ld <<= Select(phase,
            1,
            0,
            1,
            0,
            0,
            0,
        )

        self.l_bus_d_ld <<= Select(phase,
            1,
            0,
            1,
            0, # SWAP cycle: in here we put l_bus_d into l_alu_result
            (self.inst_field_opcode == INST_SWAP),
            (self.inst_field_opcode != INST_SWAP),
        )

        self.l_bus_d_select <<= Select(phase,
            LBusDSelect.bus_d, # Instruction fetch, capture it for write-back
            LBusDSelect.bus_d, # Doesn't matter, latch is disabled
            LBusDSelect.bus_d, # Data fetch, capture it for write-back
            LBusDSelect.bus_d, # SWAP cycle: Doesn't matter, latch is disabled
            LBusDSelect.alu_result, # Capture ALU result
            LBusDSelect.l_alu_result # Capture ALU result for result write-back
        )

        self.l_alu_result_ld <<= Select(phase,
            1,
            0,
            0,
            1, # Capture result in l_alu_result for SWAP instructions
            (self.inst_field_opcode != INST_SWAP), # Capture result in l_alu_result in non-SWAP instructions only
            0,
        )

        self.l_inst_ld <<= Select(phase,
            1,
            0,
            0,
            0,
            0,
            0,
        )

        is_branch = update_reg & (self.inst_field_opa == OPA_PC)
        l_was_branch.input_port <<= is_branch
        l_was_branch.latch_port <<= phase == 5

        self.l_pc_ld <<= Select(phase,
            0,
            1,
            0,
            0,
            0,
            is_branch,
        )

        ld_target = Select(phase,
            0,
            0,
            0,
            0,
            0,
            update_reg
        )

        self.l_sp_ld <<= ld_target & (self.inst_field_opa == OPA_SP)
        self.l_r0_ld <<= ld_target & (self.inst_field_opa == OPA_R0)
        self.l_r1_ld <<= ld_target & (self.inst_field_opa == OPA_R1)

        # Let's figure out what the ALU should do and on what for each cycle

        self.alu_cmd <<= Select(phase,
            AluCmds.alu_add,   # increment PC or do nothing (i.e. adding 0)
            AluCmds.alu_add,   # compute opb offset
            AluCmds.alu_add,   # compute opb offset
            AluCmds.alu_add,   # skip-cycle for SWAP only
            SelectOne(
                self.inst_field_opcode == INST_SWAP,   AluCmds.alu_add,
                self.inst_field_opcode == INST_OR,     AluCmds.alu_nand,
                self.inst_field_opcode == INST_AND,    AluCmds.alu_nor,
                self.inst_field_opcode == INST_XOR,    AluCmds.alu_xor,
                self.inst_field_opcode == INST_ADD,    AluCmds.alu_add,
                self.inst_field_opcode == INST_SUB,    AluCmds.alu_add,
                self.inst_field_opcode == INST_ISUB,   AluCmds.alu_add,

                self.inst_field_opcode == INST_ROR,    AluCmds.alu_ror,
                self.inst_field_opcode == INST_ROL,    AluCmds.alu_rol,
                self.inst_field_opcode == INST_MOV,    AluCmds.alu_add,
                self.inst_field_opcode == INST_ISTAT,  AluCmds.alu_add,

                self.inst_field_opcode == INST_EQ,     AluCmds.alu_add,
                self.inst_field_opcode == INST_LTU,    AluCmds.alu_add,
                self.inst_field_opcode == INST_LTS,    AluCmds.alu_add,
                self.inst_field_opcode == INST_LES,    AluCmds.alu_add,
            ),
            AluCmds.alu_add,   # increment PC or do nothing (i.e. adding 0)
        )
        self.alu_inv_a <<= Select(phase,
            0,   # increment PC or do nothing (i.e. adding 0)
            0,   # compute opb offset
            0,   # compute opb offset
            0,   # skip-cycle for SWAP only
            SelectOne(
                self.inst_field_opcode == INST_SWAP,   0,
                self.inst_field_opcode == INST_OR,     1,
                self.inst_field_opcode == INST_AND,    1,
                self.inst_field_opcode == INST_XOR,    0,
                self.inst_field_opcode == INST_ADD,    0,
                self.inst_field_opcode == INST_SUB,    0,
                self.inst_field_opcode == INST_ISUB,   1,

                self.inst_field_opcode == INST_ROR,    0,
                self.inst_field_opcode == INST_ROL,    0,
                self.inst_field_opcode == INST_MOV,    0,
                self.inst_field_opcode == INST_ISTAT,  0,

                self.inst_field_opcode == INST_EQ,     0,
                self.inst_field_opcode == INST_LTU,    0,
                self.inst_field_opcode == INST_LTS,    0,
                self.inst_field_opcode == INST_LES,    0,
            ),
            0,   # increment PC or do nothing (i.e. adding 0)
        )
        self.alu_inv_b <<= Select(phase,
            0,   # increment PC or do nothing (i.e. adding 0)
            0,   # compute opb offset
            0,   # compute opb offset
            0,   # skip-cycle for SWAP only
            SelectOne(
                self.inst_field_opcode == INST_SWAP,   0,
                self.inst_field_opcode == INST_OR,     1,
                self.inst_field_opcode == INST_AND,    1,
                self.inst_field_opcode == INST_XOR,    0,
                self.inst_field_opcode == INST_ADD,    0,
                self.inst_field_opcode == INST_SUB,    1,
                self.inst_field_opcode == INST_ISUB,   0,

                self.inst_field_opcode == INST_ROR,    0,
                self.inst_field_opcode == INST_ROL,    0,
                self.inst_field_opcode == INST_MOV,    0,
                self.inst_field_opcode == INST_ISTAT,  0,

                self.inst_field_opcode == INST_EQ,     1,
                self.inst_field_opcode == INST_LTU,    1,
                self.inst_field_opcode == INST_LTS,    1,
                self.inst_field_opcode == INST_LES,    1,
            ),
            0,   # increment PC or do nothing (i.e. adding 0)
        )
        self.alu_c_in <<= Select(phase,
            ~l_was_branch.output_port,   # increment PC or do nothing (i.e. adding 0)
            0,   # compute opb offset
            0,   # compute opb offset
            0,   # skip-cycle for SWAP only
            SelectOne(
                self.inst_field_opcode == INST_SWAP,   0,
                self.inst_field_opcode == INST_OR,     0,
                self.inst_field_opcode == INST_AND,    0,
                self.inst_field_opcode == INST_XOR,    0,
                self.inst_field_opcode == INST_ADD,    0,
                self.inst_field_opcode == INST_SUB,    1,
                self.inst_field_opcode == INST_ISUB,   1,

                self.inst_field_opcode == INST_ROR,    0,
                self.inst_field_opcode == INST_ROL,    0,
                self.inst_field_opcode == INST_MOV,    0,
                self.inst_field_opcode == INST_ISTAT,  0,

                self.inst_field_opcode == INST_EQ,     1,
                self.inst_field_opcode == INST_LTU,    1,
                self.inst_field_opcode == INST_LTS,    1,
                self.inst_field_opcode == INST_LES,    1,
            ),
            ~is_branch,   # increment PC or do nothing (i.e. adding 0)
        )
        opb_base = SelectOne(
            self.inst_field_opb == OPB_IMMED_PC,      AluASelect.pc,
            self.inst_field_opb == OPB_IMMED_SP,      AluASelect.sp,
            self.inst_field_opb == OPB_IMMED_R0,      AluASelect.r0,
            self.inst_field_opb == OPB_IMMED,         AluASelect.zero,
            self.inst_field_opb == OPB_MEM_IMMED_PC,  AluASelect.pc,
            self.inst_field_opb == OPB_MEM_IMMED_SP,  AluASelect.sp,
            self.inst_field_opb == OPB_MEM_IMMED_R0,  AluASelect.r0,
            self.inst_field_opb == OPB_MEM_IMMED,     AluASelect.zero,
        )
        opa_select = Select(
            self.inst_field_opcode[3:2] == INST_GROUP_UNARY,
            # Binary and predicate group
            SelectOne(
                self.inst_field_opa == OPA_PC, AluASelect.pc,
                self.inst_field_opa == OPA_SP, AluASelect.sp,
                self.inst_field_opa == OPA_R0, AluASelect.r0,
                self.inst_field_opa == OPA_R1, AluASelect.r1,
            ),
            # Unary group select operand based on 'D' bit
            Select(
                self.inst_field_opcode == INST_ISTAT,
                # Not ISTAT
                Select(
                    (self.inst_field_opcode == INST_MOV) & ~self.inst_field_d,
                    # Not move or move to memory
                    Select(self.inst_field_d ^ (self.inst_field_opcode == INST_MOV),
                        # register source and destination
                        SelectOne(
                            self.inst_field_opa == OPA_PC, AluASelect.pc,
                            self.inst_field_opa == OPA_SP, AluASelect.sp,
                            self.inst_field_opa == OPA_R0, AluASelect.r0,
                            self.inst_field_opa == OPA_R1, AluASelect.r1,
                        ),
                        AluASelect.l_bus_d
                    ),
                    # Move to register
                    AluASelect.zero
                ),
                # ISTAT
                AluASelect.int_stat
            ),
        )
        self.alu_a_select <<= Select(phase,
            AluASelect.pc,   # increment PC or do nothing (i.e. adding 0)
            opb_base,   # compute opb offset
            opb_base,   # compute opb offset
            AluASelect.l_bus_d, # skip-cycle for SWAP only
            opa_select, # execute instruction
            AluASelect.pc,   # increment PC or do nothing (i.e. adding 0)
        )
        self.alu_b_select <<= Select(phase,
            Select(l_skip.output_port, AluBSelect.zero, AluBSelect.one), # increment PC by 1 or 2 or do nothing (i.e. adding 0)
            AluBSelect.immed,   # compute opb offset
            AluBSelect.immed,   # compute opb offset
            AluBSelect.zero,   # skip-cycle for SWAP only
            Select(
                (self.inst_field_opcode == INST_SWAP) | ((self.inst_field_opcode == INST_MOV) & (self.inst_field_d)),
                Select( # execute instruction
                    is_opb_mem_ref,
                    AluBSelect.l_bus_a,
                    AluBSelect.l_bus_d,
                ),
                AluBSelect.zero # For SWAP in this cycle, we move PC into L_BUS_D
            ),
            Select(l_skip.output_port, AluBSelect.zero, AluBSelect.one) # increment PC by 1 or 2 or do nothing (i.e. adding 0)
        )

        l_skip.latch_port <<= Select(phase,
            0,
            1, # Clear skip here
            0,
            0,
            1, # Set skip here, if needed
            0
        )
        raw_condition_match = SelectOne(
            self.inst_field_opcode == INST_EQ, (self.alu_z_out == 1),
            self.inst_field_opcode == INST_LTU, (self.alu_c_out == 1),
            self.inst_field_opcode == INST_LTS, (self.alu_s_out ^ self.alu_v_out),
            self.inst_field_opcode == INST_LES, (self.alu_s_out ^ self.alu_v_out) | (self.alu_z_out == 1),
        )
        condition_match = raw_condition_match ^ ~self.inst_field_d

        l_skip.input_port <<= (phase == 4) & (self.inst_field_opcode[3:2] == INST_GROUP_PREDICATE) & condition_match

        l_intdis_prev.latch_port <<= Select(phase,
            0,
            1,
            0,
            0,
            0,
            0
        )
        int_dis_next = Wire(logic)

        l_intdis_prev.input_port <<= l_intdis.output_port
        l_intdis.latch_port <<= Select(phase,
            0,
            0,
            0,
            1,
            1,
            0
        )
        int_dis_next <<= (l_intdis_prev.output_port ^ (self.inst_field_opcode == INST_SWAP) & ~self.inst_field_d) | self.rst
        l_intdis.input_port <<= int_dis_next
        self.intdis <<= l_intdis.output_port

        """
        Swap is very difficult! We might need an extra latch to implement it.
        Either that, or a whole bus to get any register into L_BUS_D in phase 3, which might be slightly less expensive.
        The ALU is occupied in PHASE 1 and 2 with offset computation (and it needs to do it twice because L_BUS_A is a latch
        that can only capture the data in phase 3 (so it needs to be ready by the beginning of phase 3) and needs to remain
        stable throughout phase 3)
        The ALU is also occupied in PHASE 3 with the actual operation (in case of a swap, it doesn't do much, just passes the data through)
        The ALU updates the PC in PHASE 0, so that's not available, but maybe in PHASE 4, it can be used?

        So, really the only thing we can do is
        -----------------------------------------
        phase 3: ALU passes register data **directly to BUS_D**, so the write outputs that, instead of L_BUS_D
        phase 4: ALU passes L_BUS_D **directly** into the destination register (actually it can pass through L_ALU_RESULT, if needed)

        This is ugly to say the least, but the only true other option is to add an extra 16-bit latch somewhere. For
        instance, have an L_BUS_D2 register, which captures L_BUS_D so it can be overwritten through the ALU in phase 3 while
        loaded into L_ALU_RESULT in the same phase (such that it's available in phase 4 for write-back). This BTW also adds an extra mux
        as L_ALU_RESULT now have two sources.

        ... I really have to think through if SWAP is all that necessary ...
        """

class Cpu(Module):
    clk = ClkPort()
    rst = RstPort()

    interrupt = Input(logic)

    bus_cmd = Output(EnumNet(BusCmds))

    bus_d_out = Output(DataType)
    bus_d_in = Input(DataType)
    bus_a = Output(DataType)

    inst_load = Output(logic) # goes high for the cycle where the instruction is fetched. Similar to the M1 cycle of the Z80

    def body(self):
        data_path = DataPath()
        sequencer = Sequencer()

        self.bus_d_out <<= data_path.bus_d_out
        self.bus_a <<= data_path.bus_a
        self.bus_cmd <<= sequencer.bus_cmd
        data_path.bus_d_in <<= self.bus_d_in

        sequencer.interrupt <<= self.interrupt
        data_path.interrupt <<= self.interrupt

        data_path.l_bus_a_ld <<= sequencer.l_bus_a_ld
        data_path.l_bus_d_ld <<= sequencer.l_bus_d_ld
        data_path.l_alu_result_ld <<= sequencer.l_alu_result_ld
        data_path.l_pc_ld <<= sequencer.l_pc_ld
        data_path.l_sp_ld <<= sequencer.l_sp_ld
        data_path.l_r0_ld <<= sequencer.l_r0_ld
        data_path.l_r1_ld <<= sequencer.l_r1_ld
        data_path.l_inst_ld <<= sequencer.l_inst_ld

        data_path.l_bus_d_select <<= sequencer.l_bus_d_select
        data_path.alu_a_select <<= sequencer.alu_a_select
        data_path.alu_b_select <<= sequencer.alu_b_select
        data_path.alu_cmd <<= sequencer.alu_cmd
        data_path.alu_inv_a_in <<= sequencer.alu_inv_a
        data_path.alu_inv_b_in <<= sequencer.alu_inv_b

        data_path.intdis <<= sequencer.intdis

        data_path.alu_c_in <<= sequencer.alu_c_in

        sequencer.alu_c_out <<= data_path.alu_c_out
        sequencer.alu_z_out <<= data_path.alu_z_out
        sequencer.alu_s_out <<= data_path.alu_s_out
        sequencer.alu_v_out <<= data_path.alu_v_out

        sequencer.inst_field_opcode <<= data_path.inst_field_opcode
        sequencer.inst_field_d <<= data_path.inst_field_d
        sequencer.inst_field_opb <<= data_path.inst_field_opb
        sequencer.inst_field_opa <<= data_path.inst_field_opa

        self.inst_load <<= sequencer.l_inst_ld


