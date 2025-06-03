#!/usr/bin/python3
from typing import *
from silicon import *
from random import randrange

from cpu import *


class TB(Module):
    a_in = Output(DataType)
    b_in = Output(DataType)
    cmd_add = Output(logic)
    cmd_nor = Output(logic)
    cmd_nand = Output(logic)
    cmd_xor = Output(logic)
    cmd_ror = Output(logic)
    cmd_rol = Output(logic)
    inv_a_in = Output(logic)
    inv_b_in = Output(logic)
    c_in = Output(logic)

    o_out = Output(DataType)
    c_out = Output(logic)
    z_out = Output(logic)
    s_out = Output(logic)
    v_out = Output(logic)

    def body(self):
        dut = Alu()

        dut.a_in <<= self.a_in
        dut.b_in <<= self.b_in
        dut.c_in <<= self.c_in
        dut.cmd_add  <<= self.cmd_add
        dut.cmd_nor  <<= self.cmd_nor
        dut.cmd_nand <<= self.cmd_nand
        dut.cmd_xor  <<= self.cmd_xor
        dut.cmd_ror  <<= self.cmd_ror
        dut.cmd_rol  <<= self.cmd_rol
        dut.inv_a_in <<= self.inv_a_in
        dut.inv_b_in <<= self.inv_b_in

        self.o_out <<= dut.o_out
        self.c_out <<= dut.c_out
        self.z_out <<= dut.z_out
        self.v_out <<= dut.v_out


    def simulate(self):
        def test_add(a,b):
            a &= 0xffff
            b &= 0xffff
            e_o = (a + b) & 0xffff
            e_c = ((a + b) >> 16) & 0x1
            e_z = ((a + b) & 0xffff) == 0
            self.a_in <<= a
            self.b_in <<= b
            self.c_in <<= 0
            self.cmd_add  <<= 1
            self.cmd_nor  <<= 0
            self.cmd_nand <<= 0
            self.cmd_xor  <<= 0
            self.cmd_ror  <<= 0
            self.cmd_rol  <<= 0
            self.inv_a_in <<= 0
            self.inv_b_in <<= 0
            yield 4
            assert self.o_out == e_o
            assert self.c_out == e_c
            assert self.z_out == e_z

        def test_a_minus_b(a,b):
            a &= 0xffff
            b &= 0xffff
            e_o = (a - b) & 0xffff
            e_c = ((a - b) >> 16) & 0x1
            e_z = ((a - b) & 0xffff) == 0
            e_v = ((a >> 15) != (b >> 15)) and ((a >> 15) != (e_o >> 15))
            self.a_in <<= a
            self.b_in <<= b
            self.c_in <<= 1
            self.cmd_add  <<= 1
            self.cmd_nor  <<= 0
            self.cmd_nand <<= 0
            self.cmd_xor  <<= 0
            self.cmd_ror  <<= 0
            self.cmd_rol  <<= 0
            self.inv_a_in <<= 0
            self.inv_b_in <<= 1
            yield 4
            assert self.o_out == e_o
            assert self.c_out == e_c
            assert self.z_out == e_z
            assert self.v_out == e_v

        def test_b_minus_a(a,b):
            a &= 0xffff
            b &= 0xffff
            e_o = (b - a) & 0xffff
            e_c = ((b - a) >> 16) & 0x1
            e_z = ((b - a) & 0xffff) == 0
            self.a_in <<= a
            self.b_in <<= b
            self.c_in <<= 1
            self.cmd_add  <<= 1
            self.cmd_nor  <<= 0
            self.cmd_nand <<= 0
            self.cmd_xor  <<= 0
            self.cmd_ror  <<= 0
            self.cmd_rol  <<= 0
            self.inv_a_in <<= 1
            self.inv_b_in <<= 0
            yield 4
            assert self.o_out == e_o
            assert self.c_out == e_c
            assert self.z_out == e_z

        def test_and(a,b):
            a &= 0xffff
            b &= 0xffff
            e_o = (a & b) & 0xffff
            self.a_in <<= a
            self.b_in <<= b
            self.c_in <<= 1
            self.cmd_add  <<= 0
            self.cmd_nor  <<= 1
            self.cmd_nand <<= 0
            self.cmd_xor  <<= 0
            self.cmd_ror  <<= 0
            self.cmd_rol  <<= 0
            self.inv_a_in <<= 1
            self.inv_b_in <<= 1
            yield 4
            assert self.o_out == e_o

        def test_or(a,b):
            a &= 0xffff
            b &= 0xffff
            e_o = (a | b) & 0xffff
            self.a_in <<= a
            self.b_in <<= b
            self.c_in <<= 0
            self.cmd_add  <<= 0
            self.cmd_nor  <<= 0
            self.cmd_nand <<= 1
            self.cmd_xor  <<= 0
            self.cmd_ror  <<= 0
            self.cmd_rol  <<= 0
            self.inv_a_in <<= 1
            self.inv_b_in <<= 1
            yield 4
            assert self.o_out == e_o

        def test_xor(a,b):
            a &= 0xffff
            b &= 0xffff
            e_o = (a ^ b) & 0xffff
            self.a_in <<= a
            self.b_in <<= b
            self.c_in <<= 0
            self.cmd_add  <<= 0
            self.cmd_nor  <<= 0
            self.cmd_nand <<= 0
            self.cmd_xor  <<= 1
            self.cmd_ror  <<= 0
            self.cmd_rol  <<= 0
            self.inv_a_in <<= 1
            self.inv_b_in <<= 1
            yield 4
            assert self.o_out == e_o

        def test_rol(a):
            a &= 0xffff
            e_o = ((a << 1) & 0xfffe) | ((a >> 15) & 0x0001)
            self.a_in <<= a
            self.b_in <<= None
            self.c_in <<= 0
            self.cmd_add  <<= 0
            self.cmd_nor  <<= 0
            self.cmd_nand <<= 0
            self.cmd_xor  <<= 0
            self.cmd_ror  <<= 0
            self.cmd_rol  <<= 1
            self.inv_a_in <<= 0
            self.inv_b_in <<= 0
            yield 4
            assert self.o_out == e_o

        def test_ror(a):
            a &= 0xffff
            e_o = ((a >> 1) & 0x7fff) | ((a & 0x1) << 15)
            self.a_in <<= a
            self.b_in <<= None
            self.c_in <<= 0
            self.cmd_add  <<= 0
            self.cmd_nor  <<= 0
            self.cmd_nand <<= 0
            self.cmd_xor  <<= 0
            self.cmd_ror  <<= 1
            self.cmd_rol  <<= 0
            self.inv_a_in <<= 0
            self.inv_b_in <<= 0
            yield 4
            assert self.o_out == e_o


        yield from test_add(1,3)
        yield from test_add(0,0)
        yield from test_add(-1,-1)
        yield from test_add(65534,3)
        yield from test_a_minus_b(1,3)
        yield from test_a_minus_b(0,0)
        yield from test_a_minus_b(-1,-1)
        yield from test_a_minus_b(65534,3)
        yield from test_b_minus_a(1,3)
        yield from test_b_minus_a(0,0)
        yield from test_b_minus_a(-1,-1)
        yield from test_b_minus_a(65534,3)
        yield from test_and(1,3)
        yield from test_and(0,0)
        yield from test_and(-1,-1)
        yield from test_and(65534,3)
        yield from test_or(1,3)
        yield from test_or(0,0)
        yield from test_or(-1,-1)
        yield from test_or(65534,3)
        yield from test_xor(1,3)
        yield from test_xor(0,0)
        yield from test_xor(-1,-1)
        yield from test_xor(65534,3)
        yield from test_rol(1)
        yield from test_rol(0)
        yield from test_rol(-1)
        yield from test_rol(65534)
        yield from test_rol(3)
        yield from test_rol(0xaaaa)
        yield from test_rol(0x5555)
        yield from test_ror(1)
        yield from test_ror(0)
        yield from test_ror(-1)
        yield from test_ror(65534)
        yield from test_ror(3)
        yield from test_ror(0xaaaa)
        yield from test_ror(0x5555)
        print(f"DIRECTED TEST SUCCEEDED, STARTING RANDOM TESTS")
        print("ADD")
        for i in range(1000):
            yield from test_add(randrange(0x0000,0xffff), randrange(0x0000,0xffff))
        print("A_MINUS_B")
        for i in range(1000):
            yield from test_a_minus_b(randrange(0x0000,0xffff), randrange(0x0000,0xffff))
        print("B_MINUS_A")
        for i in range(1000):
            yield from test_b_minus_a(randrange(0x0000,0xffff), randrange(0x0000,0xffff))
        print("AND")
        for i in range(1000):
            yield from test_and(randrange(0x0000,0xffff), randrange(0x0000,0xffff))
        print("OR")
        for i in range(1000):
            yield from test_or(randrange(0x0000,0xffff), randrange(0x0000,0xffff))
        print("XOR")
        for i in range(1000):
            yield from test_xor(randrange(0x0000,0xffff), randrange(0x0000,0xffff))
        print("ROL")
        for i in range(1000):
            yield from test_rol(randrange(0x0000,0xffff))
        print("ROR")
        for i in range(1000):
            yield from test_ror(randrange(0x0000,0xffff))

        # Force one more event into the simulator so that it finishes populating the VCD
        self.cmd_add  <<= 0
        self.cmd_nor  <<= 0
        self.cmd_nand <<= 0
        self.cmd_xor  <<= 0
        self.cmd_ror  <<= 0
        self.cmd_rol  <<= 0
        print(f"SIMULATION TERMINATED SUCCESSFULLY")

def sim():
    def sim_top():
        return TB()

    Build.simulation(sim_top, "tb_alu.vcd", add_unnamed_scopes=True)

if __name__ == "__main__":
    sim()

