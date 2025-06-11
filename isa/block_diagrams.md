Data-plane block diagram (renders nicely in https://ivanceras.github.io/svgbob-editor/)


```
,------------------------------------- ALU_RESULT -------------------------.         +------+----+     ,-----.     ,---.
|                                                                          |         |OPCODE|REG |     |     |<----|RST|
|                                                                          |         +------+    |     |     |     `---'
|                                                                          |         | OPB  |    |     |INST |     ,---.
|                                                                          |         +------+INST|<----| MUX |<----|INT|
|                                                                          |         | OPA  |    |     |     |     `---'
|     +----+     ,-----.                                                   |         +------+    |     |     |
|     |REG |     |     |         ,---------------------------------------------------|IMMED |    |     |     |<---.
|     |    |     |     |         |                                         |         +------+----+     `-----'    |
+---->| PC |---->|     |         |                  ,-----.                |                                      |
|     |    |     |     |         |                  |     |                |                                      |
|     |    |     |     |         |                  |     |                |                                      |
|     +----+     |     |--------------------------->|     |                |                                      |
|                |     |         |                  |     |     +-----+    |                                      |
|     +----+     |     |         |                  |     |     |REG  |    |                                      |
|     |REG |     |     |         |                  |     |     |     |    |                                      |
|     |    |     |     |         |                  | ALU |---->|ALU_R|----+                                      |
+---->| SP |---->|     |         |     ,-----.      |     |     |     |    |                                      |
|     |    |     |     |         |     |     |      |     |     |     |    |                                      |
|     |    |     |     |         |     |     |      |     |     +-----+    |                                      |
|     +----+     |     |         `---->|     |----->|     |                |                                      |
|                |     |               |     |      |     |                |                                      |
|     +----+     |ALU_A|     ,---.     |ALU_B|      |     |                |                                      |
|     |REG |     | MUX |     | 0 |---->| MUX |      `-----'                |                                      |
|     |    |     |     |     `---'     |     |                             |                                      |
+---->| R0 |---->|     |               |     |                             |                                      |
|     |    |     |     |         ,---->|     |                             |                                      |
|     |    |     |     |         |     |     |                             |                                      |
|     +----+     |     |         |     `-----'                             |                                      |
|                |     |         |                                         |                                      |
|     +----+     |     |         |                                         |                                      |
|     |REG |     |     |         |                                         |                                      |
|     |    |     |     |         |                                         |                                      |
`---->| R1 |---->|     |         `----------------------------------------------------------+---------------------'
      |    |     |     |                                                   |                |
      |    |     |     |                                                   |                |
      +----+     |     |                                                   |                |
                 |     |                                                   |                |
       ,---.     |     |                                                   |                |
       | 0 |---->|     |                                                   |                |
       `---'     |     |                                                   |                |
                 |     |                                                   |                |
       ,---.     |     |                     ,-----------------------------+       +--------+
       | 1 |---->|     |                     |                             |       |        |
       `---'     |     |                     |                             |       |        |
                 |     |                     |                             v       v        |
      ,------.   |     |                     |                           ,-----------.      |
      |INTDIS|   |     |                     |                           |BUS_D  MUX |      |
      |      |-->|     |                     |                           `-----------'      |
      | INT  |   |     |                     |                                 |            |
      `------'   |     |                     |                                 |            |
                 |     |                     |                                 |            |
                 |     |                     v                                 v            |
        .------->|     |               +-----------+                     +-----------+      |
        |        |     |               |REG  BUS_A |                     |REG  BUS_D |      |
        |        `-----'               +-----------+                     +-----------+      |
        |                                    |                                 |            |
        `------------------------------------+                                 +------------'
                                             |                                 |
                                             |                                 |
                                             v                                 v

                                    ADDRESS TO MEMORY                    DATA TO MEMORY
```
TOOD: I don't think this data-flow supports SWAP.

Multiplexers are implemented using distributed OR gates. That is: PFETs on the outputs of the drivers and pull-down somewhere to create the default 0. This works well for ALU_A and ALU_B muxes. INST MUX can work that we as well, but 3 bits would need to be drive to '1' as well to implement the NOP constant.

There are extra registers that participate (mostly) in the control plane. These are:

- INTDIS
- INHIBIT
- REG_ICYCLE
- REG_ALU_CMD
- REG_BUS_CMD

The control state machine needs the following inputs:
- ALU_C
- ALU_S
- ALU_Z
- OPCODE
- OPA
- OPB
- REG_ICYCLE
- INHIBIT
- INTDIS
- INT

The following control signals need to be generated:

- REG_PC_LD
- REG_SP_LD
- REG_R0_LD
- REG_R1_LD
- ALU_A_PC
- ALU_A_SP
- ALU_A_R0
- ALU_A_R1
- ALU_A_INTSTAT
- ALU_A_BUS_A
- ALU_B_IMMED
- ALU_B_BUS_D
- REG_ALU_A_LD   <-- maybe we do this in every cycle?
- REG_ALU_B_LD   <-- maybe we do this in every cycle?
- REG_ALU_CMD_LD <-- maybe we do this in every cycle?
- ALU_CMD        <-- this is several wires, at least 4, probably more
- REG_BUS_A_LD
- REG_BUS_D_LD
- BUS_CMD
- REG_BUS_CMD_LD <-- maybe we do this in every cycle?
- INST_NOP
- INST_BUS_D
- REG_INST_LD
- ICYCLE
- INHIBIT_SET
- INHIBIT_CLR
- INTDIS_SET
- INTDIS_CLR
- BUS_D_BUS_D
- BUS_D_ALU_RESULT
- BUS_D_OE       <-- this is the same as WRITE_2, but calling it out for clarity


So we need to generate about 30-35 signals based on 16 or so inputs. That's not a small state-machine, though - of course - can be easily done by a few EPROMs. Not so much with transistors, so let's hope it partitions nicely.

Here's an idea: since (if) the ALU is uses a ripple-carry implementation, it's not going to be faster than a bit-serial ALU implementation. So, what if we did that? This would make the ALU buses single-bit and most of the registers into shift-registers. Shift-register (I think) can be implemented using latches, if they get a divided-down clock: they will shift on both clock edges.

But, if we have a bit-serial implementation of the ALU, maybe we should embrace the bit-serial nature fully? Not sure what that would mean for control for instance. But, maybe we could make things go faster as we don't necessarily have to make all cycles the same length: whenever we don't have an ALU operation, those cycles can go faster, provided the memory can go faster.

One could also look at the carry-skip adder: https://en.wikipedia.org/wiki/Carry-skip_adder. This is approximately twice as fast as a ripple-carry adder would be, but requires a parallel implementation.