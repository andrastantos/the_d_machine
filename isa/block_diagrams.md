Data-plane block diagram


```
,--------------------------------------ALU_RESULT------------------------.         ,------+----.     ,-----.     ,---.
|                                                                        |         |OPCODE|REG |     |     |<----| 0 |
|                                                                        |         +------+    |     |     |     `---'
|                                                                        |         | OPB  |    |     |INST |     ,---.
|                                                                        |         +------+INST|<----| MUX |<----|NOP|
|                                                                        |         | OPA  |    |     |     |     `---'
|     ,----.     ,-----.                                                 .         +------+    |     |     |
|     |REG |     |     |         ,-------------------------------------------------|IMMED |    |     |     |<---.
|     |    |     |     |         |                                       .         `------+----'     `-----'    |
+---->| PC |---->|     |         |                 ,-----.     ,-----.   |                                      |
|     |    |     |     |         |                 |REG  |     |     |   |                                      |
|     |    |     |     |         .                 |     |     |     |   |                                      |
|     `----'     |     |-------------------------->|ALU_A|---->|     |   |                                      |
|                |     |         .                 |     |     |     |   |                                      |
|     ,----.     |     |         |                 |     |     |     |   |                                      |
|     |REG |     |     |         |                 `-----'     |     |   |                                      |
|     |    |     |     |         |                             | ALU |---+                                      |
+---->| SP |---->|     |         |     ,-----.     ,-----.     |     |   |                                      |
|     |    |     |     |         |     |     |     |REG  |     |     |   |                                      |
|     |    |     |     |         |     |     |     |     |     |     |   |                                      |
|     `----'     |     |         `---->|     |---->|ALU_B|---->|     |   |                                      |
|                |     |               |     |     |     |     |     |   |                                      |
|     ,----.     |ALU_A|     ,---.     |ALU_B|     |     |     |     |   |                                      |
|     |REG |     | MUX |     | 0 |---->| MUX |     `-----'     `-----'   |                                      |
|     |    |     |     |     `---'     |     |                           |                                      |
+---->| R0 |---->|     |               |     |                           |                                      |
|     |    |     |     |         ,---->|     |                           |                                      |
|     |    |     |     |         |     |     |                           |                                      |
|     `----'     |     |         |     `-----'                           |                                      |
|                |     |         |                                       |                                      |
|     ,----.     |     |         |                                       |                                      |
|     |REG |     |     |         |                                       |                                      |
|     |    |     |     |         |                                       .                                      |
`---->| R1 |---->|     |         `--------------------------------------------------------+---------------------'
      |    |     |     |                                                 .                |
      |    |     |     |                                                 |                |
      `----'     |     |                                                 |                |
                 |     |                                                 |                |
       ,---.     |     |                     ,---------------------------+       +--------+
       | 0 |---->|     |                     |                           |       |        |
       `---'     |     |                     |                           |       |        |
                 |     |                     |                           \/      \/       |
      ,------.   |     |                     |                         ,-----------.      |
      |INTDIS|   |     |                     |                         |BUS_D  MUX |      |
      |      |-->|     |                     |                         `-----------'      |
      | INT  |   |     |                     |                               |            |
      `------'   |     |                     |                               |            |
                 |     |                     |                               |            |
                 |     |                     \/                              \/           |
        .------->|     |               ,-----------.                   ,-----------.      |
        |        |     |               |REG  BUS_A |                   |REG  BUS_D |      |
        |        `-----'               `-----------'                   `-----------'      |
        |                                    |                               |            |
        `---------------------------BUS_A----+                               +--BUS_D-----'
                                             |                               |
                                             |                               |
                                             \/                              \/
```

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