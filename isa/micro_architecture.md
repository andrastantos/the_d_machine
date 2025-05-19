Basic considerations
=====================

We have 3 ALU operations to perform for every instruction:

1. Increment PC
2. Compute memory reference (this needs instruction field)
3. Perform actual ALU operation

We also have 4 memory cycles to complete:

  a. Read instruction (this needs PC)
  b. Write instruction back
  c. Read operand (this needs memory reference)
  d. Write operand

'a' needs '1' and 'c' needs '2', while '2' needs '1'; also, if possible '2' and '3' needs to precede '1' so that PC-related operations reference the current PC, not the next one.

So, the cycles are:

Cycle    ALU op                            Memory op
======   ============================      ===========
1        -                                 Read instruction
2        Compute memory reference          Write instruction back
3        -                                 Read operand
4        Perform actual ALU operation      -
5        Increment PC                      Write operand

I don't think we can save any cycles here:

'2' needs '1' to complete for both of it's operations
'3' needs the memory reference, so it can't happen earlier
'4' needs the operand read, so again, can't happen before '3'
'5' needs '4' for the result to be ready.

The only way to save a cycle is if:

1. We don't allow write-back of ALU results, thus the write-back can happen during '4'
2. We give up on the PC pointing to the current instruction and increment the PC during '1'.

Given the very limited number of registers, if the are the only ones that can be a target for an instruction, we introduce a ton of spills into the code, which - at this rate - would take 4 cycles. So it's only worth it if there are no more than 25% extra spills introduced. That's hard to believe, actually, so I think I'll go with the 5-cycle implementation, however painful the non-power-of-two thing looks.

Memory implementation notes
=============================

The core memory timing is rather finicky and includes a lot of sub-cycles. It is detailed in the core memory manual page 37 onwards. A read or write cycle takes 500ns total (I think, at least). There are several sub-steps 25ns apart.

To over-simplify, the operation is as follows:

For reading:
1. Turn on Y currents
2. Turn on X currents
3. Latch sense amplifier output

Write timing is similar:
1. Turn on Y currents
2. Turn on X currents & inhibit currents
3. Wait

Note that the timing of step 3, especially for reading, cannot depend on system clock: the access time of the cores is a physical thing and doesn't depend on what the operating frequency is. The length of #1 and #2+#3 is rather asymmetrical as well, so we're probably better off de-coupling memory timing from CPU timing.

CPU state
=============

The CPU is build around an ALU. The ALU has a bypass-able output latch, but it's inputs are not latched:
- L_ALU_RESULT

The memory bus outputs (address and data) are also latched. Bus command is direct-driven from the state machine
- L_BUS_A
- L_BUS_D

The system bus input (BUS_D) is not latched and instead is directly written to the target latches (including L_BUS_D, if needed).

Finally there's are latches for the 4 architectural registers.
- L_PC
- L_SP
- L_R0
- L_R1

The current instruction code is latched in:
- L_INST

The following mode flops are also needed:
- INTDIS: set when interrupts are disabled
- INHIBIT: set when interrupts are inhibited (due to a predicate that disabled the following instruction)
- L_ICYCLE: a 3-bit counter (or a 5-bit one-hot counter?) to time the execution phases of an instruction

Data-flow block diagram
=======================


Operation in each cycle
========================

It would be nice for the CPU to be a bit-serial implementation, but this poses two problems:
  1. We would need extremely fast clocks (on the order of 32MHz) to finish a 16-bit operation in 500ns. I have not been able to create a shift-register of that speed. In fact, I have not been able to create a shift register that can go even beyond 10MHz at this point.
  2. We need a lot of shift registers. And shift registers need D-flops, not just latches. This balloons the transistor count to the point where a bit-parallel implementation appears to be cheaper.

That being said, there is are a couple of potential middle-grounds: a bit-serial ALU surrounded by input and output shift-registers, which can be parallel-loaded from an otherwise bit-parallel CPU. One could also consider a block-serial implementation where - say - 2 or 4 bits are processed in one clock cycle.

Either way, the ISA and the timing description below will assume a bit-parallel implementation for now.

Cycle 0:
- Increment PC:
  - set ALU_A to L_PC
  - set ALU_B to 0
  - set ALU_CMD to ADD
    - set carry-in to 1 if PC is not the target register, otherwise set it to 0
- open L_BUS_A and set its input to ALU_RESULT
  NOTE: since in the previous cycle we've also done the same ALU operation, the fact that L_ALU_A is in pass-through mode is not an issue: all its inputs are already settled, so we shouldn't have a problem meeting setup times on the memory
- set BUS_CMD to READ
  note: we don't alter ALU operation and don't update L_PC either in this cycle. This means that the ALU keeps outputting the next PC, so it's OK to keep L_BUS_A latch open for the whole cycle.
- open L_BUS_D
- Load L_INST - open L_INST and on its input mux:
  - if INHIBIT is 1, set 16b0_100_0_011_00_000000 (i.e. OR PC with 0, i.e. NOP)
  - else if INTDIS is 0 and INT is 0 (i.e. there's an enabled and pending interrupt), set 0x0000
  - else mux BUS_D
- open L_ALU_RESULT (this will load the current PC)

Cycle 1:
- close L_BUS_A -> it will maintain the instruction address while the ALU is busy
- open L_PC and set it's input to L_ALU_RESULT
- close L_BUS_D -> now it retains BUS_D
- close L_INST -> now it contains the next instruction (interrupt, NOP or otherwise)
- set BUS_CMD to WRITE
- clear INHIBIT (this can be moved to any subsequent cycle, if needed)
- Calculate sum of index register and immediate:
  - set ALU_B to the sign-extended version of the IMMED field of L_INST
  - set ALU_A to the register selected by the OPB field of L_INST
  - set ALU_CMD to ADD;C=0
- close L_ALU_RESULT

Cycle 2:
- Calculate sum of index register and immediate:
  - set ALU_B to the sign-extended version of the IMMED field of L_INST
  - set ALU_A to the register selected by the OPB field of L_INST
  - set ALU_CMD to ADD;C=0
- open L_BUS_A and set its input to ALU_RESULT
  NOTE: since in the previous cycle we've also done the same ALU operation, the fact that L_ALU_A is in pass-through mode is not an issue: all its inputs are already settled, so we shouldn't have a problem meeting setup times on the memory
- set BUS_CMD to READ, if needed or NOP otherwise
  note: we won't alter ALU operation in this cycle, so the ALU keeps outputting the read address, which is to say that it's fine to keep L_BUS_A open for the whole cycle
- open L_BUS_D and set its input to BUS_D

Cycle 4:
- close L_BUS_D -> now it contains the operand data
- close L_BUS_A -> now it contains the operand address
- Execute instruction:
  - set ALU_B to BUS_D or BUS_A, depending on addressing mode
  - set ALU_A to OPA-selected register or 0. OPA is of course the appropriate field of L_INST
  - set ALU_CMD based on OPCODE or 'OR' if we won't write data (i.e. we get the original data out)
- set BUS_CMD to WRITE - NOTE: here we unconditionally write back our input result. If the target was memory, we will do a second write in cycle 5.
- open L_ALU_RESULT

Cycle 5:
- close L_ALU_RESULT
- Write back result into CPU state:
  - open target register - if any - and set its input to L_ALU_RESULT.
  - set INHIBIT, if needed
  - flip INTDIS, if needed
- Increment PC:
  - set ALU_A to L_PC
  - set ALU_B to 0
  - set ALU_CMD to ADD
    - set carry-in to 1 if PC is not the target register, otherwise set it to 0
- Write back result into memory:
  - open L_BUS_D and set its input to L_ALU_RESULT, if required based on INST
  - set BUS_CMD to WRITE, if needed or NOP otherwise

Here we set up pretty long logical chains:
- Get through L_INST
- Get through the ALU input MUX (from a register)
- Get through the ALU
- Get through the output MUX
All this in a single cycle; granted that cycle is now 500ns.

I think this wavedrom script captures what's going on relatively well:

{signal: [
  {name: 'phase', wave:'4333338', data: [4,0,1,2,4,5,0]},
  {name: 'clk', wave: 'p......'},
  {name: 'BUS_CMD', wave: '6555557', data: ['write/idle','read', 'write', 'read/idle', 'write/idle', 'write/idle', 'read']},
  {name: 'L_BUS_A_ld',      wave: '01010.1'},
  {name: 'L_BUS_A', wave: '65.5..7', data: ['OP--', 'PC', 'opb_result', 'PC+1']},
  {name: 'L_BUS_D_ld',      wave: '1.0101.'},
  {name: 'BUS_D_in', wave: 'x5x5x.', data: ['INST', 'data'], phase: -1.5},
  {name: 'L_BUS_D', wave: '6x5x55x', data: ['op_result--','INST', 'data', 'op_result']},
  {},
  {name: 'L_INST_ld',       wave: '010...1'},
  {name: 'L_INST', wave: '6x5...x', data: ['INST--', 'INST']},
  {},
  {name: 'ALU_A', wave: '6.5.55.', data: [ 'PC-1', 'reg[OPB]', 'reg[OPA]', 'PC']},
  {name: 'ALU_B', wave: '6.5.55.', data: ['0', 'IMM', 'data??', '0']},
  {name: 'ALU_CMD', wave: '6.5.55.', data: ['INC/NOP--', 'ADD', 'OPCODE', 'INC/NOP']},
  {name: 'ALU use', wave: '6.5.55.', data: ['update PC--', 'compute OPB', 'execute', 'update PC']},
  {name: 'phase', wave:'4333338', data: [4,0,1,2,4,5,0]},
  {name: 'ALU_RESULT', wave: '5.5.57', data: ['PC', 'opb_result', 'op_result', 'PC+1'], phase: -1.5},
  {name: 'L_ALU_RESULT_ld', wave: '010.10.'},
  {name: 'L_ALU_RESULT', wave: '6x5.x5.', data: ['op_result--','PC', 'op_result']},
  {},
  {name: 'L_PC_ld',         wave: '0.10...'},
  {name: 'L_PC', wave: '6.5....', data: ['PC-1', 'PC']},
  {},
  {name: 'L_<target_reg>_ld', wave: '0....10'},
],
config: { hscale: 2 }
}




System design
===============

ROM
---

Not quite sure how, but a simple boot-loader will be needed that is swapped into the instruction space upon reset (based on some jumper or something). This ROM would only be consulted during the instruction fetch cycles (cycle 0), reads and writes would still go to core memory. This swapping will be controlled by a single bit that can be written (memory-mapped I/O) to disable the boot ROM and enable full access to memory. The fact that an instruction fetch is happening is communicated to the memory by the 'inst_load' signal.

NOTE: loading arbitrary constants is problematic with this setup, though immediates of course can be used. I will need to experiment more to know if this is a serious limitation.

An alternative implementation could be that the boot-swap bit inverts MSB-1 of the address bus, if MSB is 0. This is a bit more complicated, but maybe not all that much and keeps the ROM in the memory map all the time.

I/O
---

peripherals will be mapped to the top of the address space (0xffff and such) because those addresses can be reached using the immediate field alone.

In terms of actual peripherals, I'm thinking about the following:

- A simple serial port, probably 9600 baud or something, bit-banged, with also bit-banged HW flow-control; essentially two input and two output bits.

    Set flow-control:
    1. load proper constant into R1
    2. Store R1 into appropriate register to assert CTS
    Start detection:
    1. Read from port
    2. Mask with constant
    3. If 1 ...
    4. go to 1
    sync_detected:
    5. Wait for middle of bit 0 (i.e. wait ~1.5 bit-times)
    read_byte:
    1. Load 8 into R0
    2. Read from port to R1
    3. Mask with constant
    4. shift memory location (maybe SP based?)
    5. or memory location with R1
    6. wait long enough (i.e. ~1 bit-time)
    7. decrement R0
    8. If R0 is not zero ...
    9. go to #2
    wait for stop bit
    1. Read from port to R1
    2. Mask with constant
    3. If 0 ...
    4. goto 1
    Set flow-control:
    1. load proper constant into R1
    2. Store R1 into appropriate register to de-assert CTS

    Transmit would be even more straightforward. So, I really think a serial port could be bit-banged, even at 19200 baud. Or at 9600 baud if we can only hit a 1MHz CPU clock rate.

- A tape drive - this one I hope could be a 4- or 8-track cassette tape with full electronic control. The signal would be MFM modulated, probably at 2400 or 4800 baud; each symbol would have 4/8 bits and be blocked into 256 word (i.e. 1024/512 symbols) blocks. A proper sync sequence at the beginning would establish synchronization and a large enough gap between blocks would be needed to allow for tape mechanism slop. A 16-bit check-sum in the end would allow for error-detection. All of that TBD and would depend on what I can get my hands on. This would provide for ~1-4kByte/sec transfer rates. A 32kByte core memory would be filled in about half a minute, or even faster. A 60minute tape would have somewhere on the order of 3-12MByte of capacity. It would be nice if we could bit-bang this as well, but the rules are more complicated:

1 encodes as 10 if the line-state is 1, otherwise 01. In other words, a 1 inverts the line-state at the middle of the bit-time
0 encodes as 11 if the line-state was 01 or 00, 00 otherwise. In other words it generates and edge at the bit-time boundary, if more than 3 consecutive values of the same line-state would be generated.

Managing all this state for 4/8 parallel streams and do edge-detect (potentially independently) on all of them is going to be problematic.

If however we assume that edge-detect can be done on the symbol level (which could be a reasonable assumption) one could do smart things. Also, let's not forget that we have (at 4800 baud and ~2MHZ CPU clock) roughly 80 instructions for every symbol, or 40 instructions between every possible edge. An edge-detect loop would look like this:

pre-delay:
1. load pre-delay value into R1
2. decrement R1
3. NOP
4. if R1 != 0 ...
5. goto 2.
look for edge:
1. increment R1
2. Read input port into R0
3. if same as previous state (which is in memory somewhere)...
4. go to 1.
update pre-delay:
1. if previous delay value was greater than R1 (i.e. we needed to wait less) ...
2. decrement pre-delay in memory
3. if previous delay value was larger than R1 (i.e. we needed to wait more) ...
4. increment pre-delay in memory
5. store R1 into previous delay value

So, we can detect edges in 4 instructions, i.e. with an uncertainty of ~5% of a bit-time, which is the shortest pulse on the tape. That should be plenty sufficient. We also do a pre-delay to only look for edges when they are roughly expected (say +/-15% of their expected location) and update it's value to allow for tape stretching and motor speed variations.

Once we have an edge, we also should wait a little and re-read the port to make sure all bit-lanes have properly settled:
1. Read input port into R0
2. SWAP R0 and previous state
3. R0 = XOR previous state
4. Store R0 as the recovered symbol (wow, that was easy!!!)

This is done for the center of the bit-times. For bit-time boundaries, the process is:

1. Read input port into R0
2. SWAP R0 and previous state

This whole business easily fits within the times needed, so, again bit-banging should be more than sufficient.

I/O port layout
-----------------
0xfffc: switches
0xfffd: buttons
0xfffe: blinken lights
0xffff: bit0: boot-memory swap; reset to 0 by reset, set to 1 by SW, when boot is done
        rest: 7-segment control?

### SERIAL port
0xfff8: bit0: RXT
0xfff9: bit0: TXD
0xfffa: bit0: RTS
0xfffb: bit0: CTS

### TAPE
0xfff0: recording bits
0xfff1: playback bits
0xfff2: tape control (each bit for a different transport button)

