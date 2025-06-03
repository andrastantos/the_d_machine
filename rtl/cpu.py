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

AddrWidth = 16
DataWidth = 16
AddrType = Unsigned(AddrWidth)
DataType = Unsigned(DataWidth)


# ADD:   and_en_n=1 or_en_n=0 rol_en=0 ror_en=0 cout_0=0 cout_1=0
# XNOR:  and_en_n=1 or_en_n=X rol_en=0 ror_en=0 cout_0=0 cout_1=1 c_in=1
# XOR:   and_en_n=X or_en_n=0 rol_en=0 ror_en=0 cout_0=1 cout_1=0 c_in=0
# NOR:   and_en_n=0 or_en_n=X rol_en=0 ror_en=0 cout_0=0 cout_1=1 c_in=1
# NAND:  and_en_n=X or_en_n=1 rol_en=0 ror_en=0 cout_0=1 cout_1=0 c_in=0
# MOV_A: and_en_n=1 or_en_n=0 rol_en=0 ror_en=0 cout_0=1 cout_1=0 c_in=0 a_in=X b_in=0
# MOV_B: and_en_n=1 or_en_n=0 rol_en=0 ror_en=0 cout_0=1 cout_1=0 c_in=0 a_in=0 b_in=X
# ROL:   and_en_n=X or_en_n=1 rol_en=1 ror_en=0 cout_0=1 cout_1=0 c_in=0 a_in=X b_in=0
# ROR:   and_en_n=X or_en_n=1 rol_en=0 ror_en=1 cout_0=1 cout_1=0 c_in=0 a_in=X b_in=0

def repeat(signal, count):
    return concat(*([signal]*count))

class AluBitSlice(Module):
    a_prev_n = Input(logic)
    a_next_n = Input(logic)
    a_in = Input(logic)
    b_in = Input(logic)
    nand_en = Input(logic)
    nor_en_n = Input(logic)
    inv_a_in = Input(logic)
    inv_a_in_n = Input(logic)
    inv_b_in = Input(logic)
    inv_b_in_n = Input(logic)
    c_in = Input(logic)
    rol_en = Input(logic)
    ror_en = Input(logic)
    and1_en = Input(logic)

    cout_0_n = Input(logic)
    cout_1 = Input(logic)

    a_n_out = Output(logic)
    o_out = Output(logic)
    c_out = Output(logic)

    def body(self):
        a_n = not_gate(self.a_in)
        b_n = not_gate(self.b_in)
        self.a_n_out <<= a_n
        a = or_gate(and_gate(self.inv_a_in, a_n), and_gate(self.inv_a_in_n, self.a_in))
        b = or_gate(and_gate(self.inv_b_in, b_n), and_gate(self.inv_b_in_n, self.b_in))
        # generating bit output
        onand = not_gate(and_gate(a, b, self.c_in, self.nand_en))
        onor = not_gate(or_gate(a, b, self.c_in, self.nor_en_n))
        and1 = and_gate(a, b, onand, self.and1_en)
        and2 = and_gate(a, self.c_in, onand)
        and3 = and_gate(b, self.c_in, onand)
        rol_and = and_gate(self.rol_en, self.a_prev_n)
        ror_and = and_gate(self.ror_en, self.a_next_n)
        final_or = or_gate(onor, and1, and2, and3, rol_and, ror_and)
        self.o_out <<= not_gate(final_or)

        # generating carry
        cand1 = and_gate(a, b, self.cout_0_n)
        cand2 = and_gate(a, self.c_in, self.cout_0_n)
        cand3 = and_gate(b, self.c_in, self.cout_0_n)
        cor = or_gate(cand1, cand2, cand3, self.cout_1)
        self.c_out <<= not_gate(not_gate(cor))



class Alu(Module):
    a_in      = Input(DataType)
    b_in      = Input(DataType)
    cmd_add   = Input(logic) # 1-hot encoded command code signals
    cmd_nor   = Input(logic) # ...
    cmd_nand  = Input(logic) # ...
    cmd_xor   = Input(logic) # ...
    cmd_ror   = Input(logic) # ...
    cmd_rol   = Input(logic) # ...
    inv_a_in  = Input(logic)
    inv_b_in  = Input(logic)
    c_in      = Input(logic)

    o_out = Output(DataType)
    c_out = Output(logic)
    z_out = Output(logic)
    s_out = Output(logic)
    v_out = Output(logic)

    def body(self):
        alu_array: Sequence[AluBitSlice] = []
        carry_chain = Wire(DataType)
        data_size = self.a_in.get_num_bits()
        c_chain = self.c_in
        inv_a_in_n = not_gate(self.inv_a_in)
        inv_b_in_n = not_gate(self.inv_b_in)

        bitslice_nand_en = not_gate(self.cmd_nor)
        bitslice_nor_en_n = and_gate(not_gate(self.cmd_add), not_gate(self.cmd_xor))
        bitslice_and1_en = and_gate(not_gate(self.cmd_rol) & not_gate(self.cmd_ror))
        bitslice_rol_en = self.cmd_rol
        bitslice_ror_en = self.cmd_ror
        bitslice_cout_0_n = or_gate(self.cmd_add, self.cmd_nor)
        bitslice_cout_1 = self.cmd_nor

        for i in range(data_size):
            bitslice = AluBitSlice()
            # register a name for this slice by adding it as an attribute
            #setattr(self, f"bitslice_{i}", bitslice)
            scope_table = self._impl.netlist.symbol_table[self._impl._true_module]
            scope_table.add_hard_symbol(bitslice, f"bitslice_{i}")
            alu_array.append(bitslice)
            bitslice.a_in <<= self.a_in[i]
            bitslice.b_in <<= self.b_in[i]
            #if i == 0:
            #    bitslice.c_in <<= self.c_in
            #else:
            #    bitslice.c_in <<= carry_chain[i-1]
            bitslice.c_in <<= c_chain
            bitslice.inv_a_in <<= self.inv_a_in
            bitslice.inv_a_in_n <<= inv_a_in_n
            bitslice.inv_b_in <<= self.inv_b_in
            bitslice.inv_b_in_n <<= inv_b_in_n

# ADD:   and_en_n=1 or_en_n=0 rol_en=0 ror_en=0 cout_0=0 cout_1=0
# XOR:   and_en_n=X or_en_n=0 rol_en=0 ror_en=0 cout_0=1 cout_1=0 c_in=0
# NOR:   and_en_n=0 or_en_n=X rol_en=0 ror_en=0 cout_0=0 cout_1=1 c_in=1
# NAND:  and_en_n=X or_en_n=1 rol_en=0 ror_en=0 cout_0=1 cout_1=0 c_in=0
# ROL:   and_en_n=X or_en_n=1 rol_en=1 ror_en=0 cout_0=1 cout_1=0 c_in=0 a_in=X b_in=0
# ROR:   and_en_n=X or_en_n=1 rol_en=0 ror_en=1 cout_0=1 cout_1=0 c_in=0 a_in=X b_in=0

            bitslice.nand_en  <<= bitslice_nand_en
            bitslice.nor_en_n <<= bitslice_nor_en_n
            bitslice.and1_en  <<= bitslice_and1_en
            bitslice.rol_en   <<= bitslice_rol_en
            bitslice.ror_en   <<= bitslice_ror_en
            bitslice.cout_0_n <<= bitslice_cout_0_n
            bitslice.cout_1   <<= bitslice_cout_1

            self.o_out[i] <<= bitslice.o_out
            #carry_chain[i] <<= bitslice.c_out
            c_chain = bitslice.c_out
            carry_chain[i] <<= c_chain

        # Now that we have all the slices, we can hook up the ROL/ROR chains
        for i, bitslice in enumerate(alu_array):
            bitslice.a_prev_n <<= alu_array[(i-1) % data_size].a_n_out
            bitslice.a_next_n <<= alu_array[(i+1) % data_size].a_n_out

        del bitslice # clean up the namespace a little

        self.c_out <<= c_chain ^ (self.inv_a_in | self.inv_b_in)
        self.z_out <<= self.o_out == 0
        self.s_out <<= self.o_out[15]
        # overflow for now is only valid for a_minus_b (which is what all the predicates use)
        # See https://en.wikipedia.org/wiki/Overflow_flag for details
        minuend_msb = self.a_in[15] #Select(self.inv_b_in, self.b_in[15], self.a_in[15])
        self.v_out <<= (self.a_in[15] != self.b_in[15]) & (minuend_msb != self.o_out[15])


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

    l_bus_d_load_bus_d = Input(logic)
    l_bus_d_load_alu_result = Input(logic)
    l_bus_d_load_l_alu_result = Input(logic)

    alu_a_select_pc = Input(logic)
    alu_a_select_sp = Input(logic)
    alu_a_select_r0 = Input(logic)
    alu_a_select_r1 = Input(logic)
    alu_a_select_zero = Input(logic)
    alu_a_select_int_stat = Input(logic)
    alu_a_select_l_bus_d = Input(logic)

    alu_b_select_immed = Input(logic)
    alu_b_select_zero = Input(logic)
    alu_b_select_one = Input(logic)
    alu_b_select_l_bus_d = Input(logic)
    alu_b_select_l_bus_a = Input(logic)

    alu_cmd_add   = Input(logic) # 1-hot encoded command code signals
    alu_cmd_nor   = Input(logic) # ...
    alu_cmd_nand  = Input(logic) # ...
    alu_cmd_xor   = Input(logic) # ...
    alu_cmd_ror   = Input(logic) # ...
    alu_cmd_rol   = Input(logic) # ...

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

        alu = Alu()
        alu_result <<= alu.o_out
        self.alu_c_out <<= alu.c_out
        self.alu_z_out <<= alu.z_out
        self.alu_s_out <<= alu.s_out
        self.alu_v_out <<= alu.v_out
        alu.a_in <<= alu_a_in
        alu.b_in <<= alu_b_in
        alu.cmd_add <<= self.alu_cmd_add
        alu.cmd_nor <<= self.alu_cmd_nor
        alu.cmd_nand <<= self.alu_cmd_nand
        alu.cmd_xor <<= self.alu_cmd_xor
        alu.cmd_ror <<= self.alu_cmd_ror
        alu.cmd_rol <<= self.alu_cmd_rol
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
        l_bus_d.input_port <<= or_gate(
            and_gate(repeat(self.l_bus_d_load_bus_d, DataWidth), self.bus_d_in),
            and_gate(repeat(self.l_bus_d_load_alu_result, DataWidth), alu_result),
            and_gate(repeat(self.l_bus_d_load_l_alu_result, DataWidth), l_alu_result.output_port)
        )
        l_alu_result.input_port <<= alu_result
        l_pc.input_port <<= l_alu_result.output_port
        l_sp.input_port <<= l_alu_result.output_port
        l_r0.input_port <<= l_alu_result.output_port
        l_r1.input_port <<= l_alu_result.output_port

        serve_interrupt = and_gate(not_gate(self.intdis), self.interrupt)
        serve_interrupt_n = not_gate(serve_interrupt)


        # We're creating the input mux for the instruction latch. This is highly optimized because the only alternatives to bus_d
        # are constants. So, we examine them bit-by-bit and generate the most optimal logic. We are also careful about priorities:
        # if both reset and interrupt are asserted, reset takes priority.
        assert (INST_SWAP ^ INST_MOV).bit_count() == 1, "INST_MOV and INST_SWAP should differ in one bit only. Review instruction codes!"
        rst_inst = (INST_MOV  << OPCODE_OFS) | (DEST_REG << D_OFS) | (OPB_MEM_IMMED << OPB_OFS) | (OPA_PC << OPA_OFS) | (0 << IMMED_OFS)
        int_inst = (INST_SWAP << OPCODE_OFS) | (DEST_REG << D_OFS) | (OPB_MEM_IMMED << OPB_OFS) | (OPA_PC << OPA_OFS) | (1 << IMMED_OFS)
        int_or_reset = or_gate(serve_interrupt, self.rst)
        rst_n = not_gate(self.rst)
        int_or_reset_n = not_gate(int_or_reset)
        l_inst_input = Wire(DataType)
        # TODO: not sure what the iteration order is: is it MSB or LSB first? At any rate, since the instructions at the moment are symmetrical,
        #       it doesn't matter.
        for idx, (l_inst_bit, bus_d_in_bit) in enumerate(zip(l_inst_input, self.bus_d_in)):
            rst_inst_bit = (rst_inst >> idx) & 1
            int_inst_bit = (int_inst >> idx) & 1
            if rst_inst_bit == int_inst_bit:
                if rst_inst_bit == 0:
                    # The alternate bit is 0, we can get away with an AND gate
                    l_inst_bit <<= and_gate(int_or_reset_n, bus_d_in_bit)
                else:
                    # Alternate bit is 1, this is an OR gate
                    l_inst_bit <<= or_gate(int_or_reset, bus_d_in_bit)
            else:
                # Reset and interrupts are different, we'll have to be more considerate
                if int_inst_bit == 1:
                    int_or_inst = or_gate(serve_interrupt, bus_d_in_bit)
                else:
                    int_or_inst = and_gate(serve_interrupt_n, bus_d_in_bit)
                if rst_inst_bit == 1:
                    l_inst_bit <<= or_gate(self.rst, int_or_inst)
                else:
                    l_inst_bit <<= and_gate(rst_n, int_or_inst)
        del rst_inst_bit, int_inst_bit, l_inst_bit, bus_d_in_bit, int_or_inst
        l_inst.input_port <<= l_inst_input

        # This is the readable implementation:
        #l_inst.input_port <<= SelectFirst(
        #    serve_interrupt | self.rst, (Select(self.rst, INST_SWAP, INST_MOV) << OPCODE_OFS) | (DEST_REG << D_OFS) | (OPB_MEM_IMMED << OPB_OFS) | (OPA_PC << OPA_OFS) | ((~self.rst) << IMMED_OFS),
        #    default_port = self.bus_d_in
        #)

        alu_a_in <<= or_gate(
            and_gate(repeat(self.alu_a_select_pc, DataWidth), l_pc.output_port),
            and_gate(repeat(self.alu_a_select_sp, DataWidth), l_sp.output_port),
            and_gate(repeat(self.alu_a_select_r0, DataWidth), l_r0.output_port),
            and_gate(repeat(self.alu_a_select_r1, DataWidth), l_r1.output_port),
            and_gate(repeat(self.alu_a_select_zero, DataWidth), 0),
            and_gate(repeat(self.alu_a_select_int_stat, DataWidth), concat(self.intdis, self.interrupt)),
            and_gate(repeat(self.alu_a_select_l_bus_d, DataWidth), l_bus_d.output_port),
        )
        alu_b_in <<= or_gate(
            and_gate(repeat(self.alu_b_select_immed, DataWidth), immed),
            and_gate(repeat(self.alu_b_select_zero, DataWidth), 0),
            and_gate(repeat(self.alu_b_select_one, DataWidth), 1),
            and_gate(repeat(self.alu_b_select_l_bus_d, DataWidth), l_bus_d.output_port),
            and_gate(repeat(self.alu_b_select_l_bus_a, DataWidth), l_bus_a.output_port),
        )

        self.bus_d_out <<= l_bus_d.output_port
        self.bus_a <<= l_bus_a.output_port

### TODO: there's a huge issue here!!! Any latch load signal with glitches is highly problematic!!!!
class Sequencer(Module):
    clk = ClkPort()
    rst = RstPort()

    interrupt = Input(logic)

    bus_wr = Output(logic)
    bus_rd = Output(logic)

    l_bus_a_ld =      Output(logic)
    l_bus_d_ld =      Output(logic)
    l_alu_result_ld = Output(logic)
    l_pc_ld =         Output(logic)
    l_sp_ld =         Output(logic)
    l_r0_ld =         Output(logic)
    l_r1_ld =         Output(logic)
    l_inst_ld =       Output(logic)

    l_bus_d_load_bus_d =        Output(logic)
    l_bus_d_load_alu_result =   Output(logic)
    l_bus_d_load_l_alu_result = Output(logic)

    alu_a_select_pc       = Output(logic)
    alu_a_select_sp       = Output(logic)
    alu_a_select_r0       = Output(logic)
    alu_a_select_r1       = Output(logic)
    alu_a_select_zero     = Output(logic)
    alu_a_select_int_stat = Output(logic)
    alu_a_select_l_bus_d  = Output(logic)

    alu_b_select_immed   = Output(logic)
    alu_b_select_zero    = Output(logic)
    alu_b_select_one     = Output(logic)
    alu_b_select_l_bus_d = Output(logic)
    alu_b_select_l_bus_a = Output(logic)

    alu_cmd_add  =   Output(logic) # 1-hot encoded command code signals
    alu_cmd_nor  =   Output(logic) # ...
    alu_cmd_nand =   Output(logic) # ...
    alu_cmd_xor  =   Output(logic) # ...
    alu_cmd_ror  =   Output(logic) # ...
    alu_cmd_rol  =   Output(logic) # ...
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

        inst_is_predicate = self.inst_field_opcode[3:2] == INST_GROUP_PREDICATE
        inst_is_not_predicate = ~inst_is_predicate
        inst_is_unary = self.inst_field_opcode[3:2] == INST_GROUP_UNARY
        inst_is_not_unary = ~inst_is_unary

        inst_is_INST_SWAP  = self.inst_field_opcode == INST_SWAP
        inst_is_not_INST_SWAP = ~inst_is_INST_SWAP
        inst_is_INST_OR    = self.inst_field_opcode == INST_OR
        inst_is_INST_AND   = self.inst_field_opcode == INST_AND
        inst_is_INST_XOR   = self.inst_field_opcode == INST_XOR
        inst_is_INST_ADD   = self.inst_field_opcode == INST_ADD
        inst_is_INST_SUB   = self.inst_field_opcode == INST_SUB
        inst_is_INST_ISUB  = self.inst_field_opcode == INST_ISUB
        inst_is_INST_ROR   = self.inst_field_opcode == INST_ROR
        inst_is_INST_ROL   = self.inst_field_opcode == INST_ROL
        inst_is_INST_MOV   = self.inst_field_opcode == INST_MOV
        inst_is_not_INST_MOV   = ~inst_is_INST_MOV
        inst_is_INST_ISTAT = self.inst_field_opcode == INST_ISTAT
        inst_is_not_INST_ISTAT = ~inst_is_INST_ISTAT
        inst_is_INST_EQ    = self.inst_field_opcode == INST_EQ
        inst_is_INST_LTU   = self.inst_field_opcode == INST_LTU
        inst_is_INST_LTS   = self.inst_field_opcode == INST_LTS
        inst_is_INST_LES   = self.inst_field_opcode == INST_LES

        inst_field_d_n = ~self.inst_field_d

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

        opb_is_mem_ref = self.inst_field_opb[2] != OPB_CLASS_IMM
        # We skip over phase 4 for anything but a SWAP instruction
        l_phase_next.input_port <<= Select(
            phase == 5,
            (phase + Select(inst_is_INST_SWAP | (phase != 2), 2, 1))[2:0],
            0
        )
        phase0 = phase == 0
        phase1 = phase == 1
        phase2 = phase == 2
        phase3 = phase == 3
        phase4 = phase == 4
        phase5 = phase == 5


        update_mem <<= or_gate(
            # Swap always updates mem
            inst_is_INST_SWAP,
            # Not a predicate instruction --> field D determines if we write to memory
            and_gate(inst_is_not_predicate, opb_is_mem_ref, self.inst_field_d)
        )
        update_reg <<= or_gate(
            # Swap always updates reg
            inst_is_INST_SWAP,
            # Not a predicate instruction --> field D determines if we write to registers
            and_gate(inst_is_not_predicate, inst_field_d_n)
        )

        self.bus_wr <<= Select(self.rst,
            Select(phase,
                0,
                1,
                0,
                0, # SWAP-only cycle
                and_gate(opb_is_mem_ref, not_gate(update_mem)),
                update_mem,
            ),
            0
        )

        self.bus_rd <<= Select(self.rst,
            Select(phase,
                1,
                0,
                opb_is_mem_ref,
                0, # SWAP-only cycle
                0,
                0,
            ),
            0
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
            inst_is_INST_SWAP,
            inst_is_not_INST_SWAP,
        )

        self.l_bus_d_load_bus_d <<= Select(phase,
            1, # Instruction fetch, capture it for write-back
            0, # Doesn't matter, latch is disabled
            1, # Data fetch, capture it for write-back
            0, # SWAP cycle: Doesn't matter, latch is disabled
            0, # Capture ALU result
            0  # Capture ALU result for result write-back
        )
        self.l_bus_d_load_alu_result <<= Select(phase,
            0, # Instruction fetch, capture it for write-back
            0, # Doesn't matter, latch is disabled
            0, # Data fetch, capture it for write-back
            0, # SWAP cycle: Doesn't matter, latch is disabled
            1, # Capture ALU result
            0  # Capture ALU result for result write-back
        )
        self.l_bus_d_load_l_alu_result <<= Select(phase,
            0, # Instruction fetch, capture it for write-back
            0, # Doesn't matter, latch is disabled
            0, # Data fetch, capture it for write-back
            0, # SWAP cycle: Doesn't matter, latch is disabled
            0, # Capture ALU result
            1  # Capture ALU result for result write-back
        )

        self.l_alu_result_ld <<= Select(phase,
            1,
            0,
            0,
            1, # Capture result in l_alu_result for SWAP instructions
            inst_is_not_INST_SWAP, # Capture result in l_alu_result in non-SWAP instructions only
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
        l_was_branch.latch_port <<= phase5

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
        self.alu_cmd_nor   <<= and_gate(phase4, inst_is_INST_AND)
        self.alu_cmd_nand  <<= and_gate(phase4, inst_is_INST_OR)
        self.alu_cmd_xor   <<= and_gate(phase4, inst_is_INST_XOR)
        self.alu_cmd_ror   <<= and_gate(phase4, inst_is_INST_ROR)
        self.alu_cmd_rol   <<= and_gate(phase4, inst_is_INST_ROL)
        self.alu_cmd_add   <<= not_gate(or_gate(
            self.alu_cmd_nor,
            self.alu_cmd_nand,
            self.alu_cmd_xor,
            self.alu_cmd_ror,
            self.alu_cmd_rol,
        ))

        self.alu_inv_a <<= and_gate(phase4, or_gate(
            inst_is_INST_OR,
            inst_is_INST_AND,
            inst_is_INST_ISUB,
        ))
        self.alu_inv_b <<= and_gate(phase4, or_gate(
            inst_is_INST_OR,
            inst_is_INST_AND,
            inst_is_INST_SUB,
            inst_is_predicate
        ))
        self.alu_c_in <<= or_gate(
            and_gate(phase0, ~l_was_branch.output_port),
            and_gate(phase4, or_gate(
                inst_is_INST_AND,
                inst_is_INST_SUB,
                inst_is_INST_ISUB,
                inst_is_predicate
            )),
            and_gate(phase5, ~is_branch)
        )

        inst_field_opb_base = self.inst_field_opb[OPB_BASE_SIZE+OPB_BASE_OFS-1:OPB_BASE_OFS]
        opb_base = SelectOne(
            inst_field_opb_base == (OPB_IMMED_PC & OPB_BASE_MASK),      AluASelect.pc,
            inst_field_opb_base == (OPB_IMMED_SP & OPB_BASE_MASK),      AluASelect.sp,
            inst_field_opb_base == (OPB_IMMED_R0 & OPB_BASE_MASK),      AluASelect.r0,
            inst_field_opb_base == (OPB_IMMED    & OPB_BASE_MASK),      AluASelect.zero,
        )
        opa_reg = SelectOne(
            self.inst_field_opa == OPA_PC, AluASelect.pc,
            self.inst_field_opa == OPA_SP, AluASelect.sp,
            self.inst_field_opa == OPA_R0, AluASelect.r0,
            self.inst_field_opa == OPA_R1, AluASelect.r1,
        )
        move_to_reg =   and_gate(inst_is_INST_MOV, inst_field_d_n)
        move_to_reg_n = and_gate(not_gate(move_to_reg), inst_is_not_INST_ISTAT)
        dst_is_memory = and_gate(move_to_reg_n, self.inst_field_d, inst_is_not_INST_MOV)
        dst_is_reg =    and_gate(move_to_reg_n, or_gate(inst_field_d_n, inst_is_INST_MOV))
        opa_select = EnumNet(AluASelect)(or_gate(
            and_gate(repeat(inst_is_not_unary, 3), opa_reg),
            and_gate(repeat(inst_is_unary, 3),
                or_gate(
                    and_gate(repeat(inst_is_INST_ISTAT, 3), AluASelect.int_stat),
                    and_gate(repeat(move_to_reg,3), AluASelect.zero),
                    and_gate(repeat(dst_is_memory,3), AluASelect.l_bus_d),
                    and_gate(repeat(dst_is_reg,3), opa_reg)
                )
            )
        ))

        # Old implementation kept for documentation purposes
        #opa_select = Select(
        #    inst_is_unary,
        #    # Binary and predicate group
        #    opa_reg,
        #    # Unary group select operand based on 'D' bit
        #    Select(
        #        inst_is_INST_ISTAT,
        #        # Not ISTAT
        #        Select(
        #            inst_is_INST_MOV & inst_field_d_n,
        #            # Not move or move to memory
        #            Select(and_gate(self.inst_field_d, inst_is_not_INST_MOV),
        #                # register source and destination
        #                opa_reg,
        #                AluASelect.l_bus_d
        #            ),
        #            # Move to register
        #            AluASelect.zero
        #        ),
        #        # ISTAT
        #        AluASelect.int_stat
        #    ),
        #)

        alu_a_select = Select(phase,
            AluASelect.pc,   # increment PC or do nothing (i.e. adding 0)
            opb_base,   # compute opb offset
            opb_base,   # compute opb offset
            AluASelect.l_bus_d, # skip-cycle for SWAP only
            opa_select, # execute instruction
            AluASelect.pc,   # increment PC or do nothing (i.e. adding 0)
        )

        self.alu_a_select_pc       <<= alu_a_select == AluASelect.pc
        self.alu_a_select_sp       <<= alu_a_select == AluASelect.sp
        self.alu_a_select_r0       <<= alu_a_select == AluASelect.r0
        self.alu_a_select_r1       <<= alu_a_select == AluASelect.r1
        self.alu_a_select_zero     <<= alu_a_select == AluASelect.zero
        self.alu_a_select_int_stat <<= alu_a_select == AluASelect.int_stat
        self.alu_a_select_l_bus_d  <<= alu_a_select == AluASelect.l_bus_d


        alu_b_select = Select(phase,
            Select(l_skip.output_port, AluBSelect.zero, AluBSelect.one), # increment PC by 1 or 2 or do nothing (i.e. adding 0)
            AluBSelect.immed,   # compute opb offset
            AluBSelect.immed,   # compute opb offset
            AluBSelect.zero,   # skip-cycle for SWAP only
            Select(
                inst_is_INST_SWAP | (inst_is_INST_MOV & self.inst_field_d),
                Select( # execute instruction
                    opb_is_mem_ref,
                    AluBSelect.l_bus_a,
                    AluBSelect.l_bus_d,
                ),
                AluBSelect.zero # For SWAP in this cycle, we move PC into L_BUS_D
            ),
            Select(l_skip.output_port, AluBSelect.zero, AluBSelect.one) # increment PC by 1 or 2 or do nothing (i.e. adding 0)
        )
        self.alu_b_select_immed <<= alu_b_select == AluBSelect.immed
        self.alu_b_select_zero <<= alu_b_select == AluBSelect.zero
        self.alu_b_select_one <<= alu_b_select == AluBSelect.one
        self.alu_b_select_l_bus_d <<= alu_b_select == AluBSelect.l_bus_d
        self.alu_b_select_l_bus_a <<= alu_b_select == AluBSelect.l_bus_a


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

        l_skip.input_port <<= (phase == 4) & inst_is_predicate & condition_match

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
        int_dis_next <<= (l_intdis_prev.output_port ^ inst_is_INST_SWAP & inst_field_d_n) | self.rst
        l_intdis.input_port <<= int_dis_next
        self.intdis <<= l_intdis.output_port


class Cpu(Module):
    clk = ClkPort()
    rst = RstPort()

    interrupt = Input(logic)

    bus_wr = Output(logic)
    bus_rd = Output(logic)

    bus_d_out = Output(DataType)
    bus_d_in = Input(DataType)
    bus_a = Output(DataType)

    inst_load = Output(logic) # goes high for the cycle where the instruction is fetched. Similar to the M1 cycle of the Z80

    def body(self):
        data_path = DataPath()
        sequencer = Sequencer()

        self.bus_d_out <<= data_path.bus_d_out
        self.bus_a <<= data_path.bus_a
        self.bus_wr <<= sequencer.bus_wr
        self.bus_rd <<= sequencer.bus_rd
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

        data_path.l_bus_d_load_bus_d <<= sequencer.l_bus_d_load_bus_d
        data_path.l_bus_d_load_alu_result <<= sequencer.l_bus_d_load_alu_result
        data_path.l_bus_d_load_l_alu_result <<= sequencer.l_bus_d_load_l_alu_result

        data_path.alu_a_select_pc <<= sequencer.alu_a_select_pc
        data_path.alu_a_select_sp <<= sequencer.alu_a_select_sp
        data_path.alu_a_select_r0 <<= sequencer.alu_a_select_r0
        data_path.alu_a_select_r1 <<= sequencer.alu_a_select_r1
        data_path.alu_a_select_zero <<= sequencer.alu_a_select_zero
        data_path.alu_a_select_int_stat <<= sequencer.alu_a_select_int_stat
        data_path.alu_a_select_l_bus_d <<= sequencer.alu_a_select_l_bus_d

        data_path.alu_b_select_immed <<= sequencer.alu_b_select_immed
        data_path.alu_b_select_zero <<= sequencer.alu_b_select_zero
        data_path.alu_b_select_one <<= sequencer.alu_b_select_one
        data_path.alu_b_select_l_bus_d <<= sequencer.alu_b_select_l_bus_d
        data_path.alu_b_select_l_bus_a <<= sequencer.alu_b_select_l_bus_a

        data_path.alu_cmd_add   <<= sequencer.alu_cmd_add
        data_path.alu_cmd_nor   <<= sequencer.alu_cmd_nor
        data_path.alu_cmd_nand  <<= sequencer.alu_cmd_nand
        data_path.alu_cmd_xor   <<= sequencer.alu_cmd_xor
        data_path.alu_cmd_ror   <<= sequencer.alu_cmd_ror
        data_path.alu_cmd_rol   <<= sequencer.alu_cmd_rol

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


