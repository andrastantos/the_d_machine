; MMU access violation test for tb_fetch_av.py.
;
; Enters user mode with the MMU limit at page 8 (0x0000..0x11ff), checks
; that immediates and loaded values above the limit don't cause access
; violations, then triggers one and checks the state the handler sees.
; The handler terminates with exit code 0 on success, the saved PC if it
; is not EXPECT_PC, or 1/2 if $r0/$r1 were clobbered.
;
; With --defsym OFFSET=n the MMU offset is n pages: user code is stored at
; physical 0x1100 + n * 0x200 but runs at logical 0x1100. A decoy at
; physical 0x1100 clobbers $r0 if the first user-mode fetch isn't translated.
;
; Assemble with the TDM binutils port:
;   fetch AV (jump to page 9):
;     as --defsym EXPECT_PC=0x1201 -o av.o av.s
;   data AV (the syscall instruction, mov $r0, [-1]):
;     as --defsym EXPECT_PC=0x1103 --defsym DATA_AV=1 -o av.o av.s
; then:
;     ld -Ttext=0 -e 0 -o av.elf av.o
;     objcopy -O binary av.elf av.bin

	.ifndef	OFFSET
	.set	OFFSET, 0
	.endif
	.set	USER, 0x1100		; logical address of the user code

	.text
	.org	0
	.word	start			; MEM[0]: reset vector
	.word	handler			; MEM[1]: interrupt vector
	.word	0			; MEM[2]: scratch for swapi

	.org	0x1000
start:	mov	$r0, [$pc + (kmmu - .)]
	mov	[-1], $r0		; MMU: offset OFFSET pages, limit page 8, user mode, clear AV (reset state is unknown)
	mov	$r0, [$pc + (k01ff - .)]
	mov	[-2], $r0		; int ctrl: enable AV (source 0), clear pending
	mov	$r0, [$pc + (kuser - .)]
	mov	[2], $r0
	swapi	$pc, [2]		; enter user code with interrupts enabled
k01ff:	.word	0x01ff
kmmu:	.word	(OFFSET << 9) | (8 << 2) | (1 << 1) | 1
kuser:	.word	USER

	.org	0x1040
handler:
	mov	$sp, [1]		; saved PC
	if_neq	$sp, [$pc + (k1201 - .)]
	mov	$pc, $pc + (fail_pc - .)
	if_neq	$r0, -1
	mov	$pc, $pc + (fail_r0 - .)
	if_neq	$r1, -1
	mov	$pc, $pc + (fail_r1 - .)
	mov	$r0, 0
	mov	[-30], $r0		; success: exit code 0
	mov	$pc, $pc
fail_pc: mov	[-30], $sp		; exit code = saved PC
	mov	$pc, $pc
fail_r0: mov	$r1, 1
	mov	[-30], $r1
	mov	$pc, $pc
fail_r1: mov	$r0, 2
	mov	[-30], $r0
	mov	$pc, $pc
k1201:	.word	EXPECT_PC

	.macro	user_code
	mov	$r0, -1			; phase 1 computes 0xffff: must not AV
	mov	$r1, [$pc + (kffff - .)]	; phase 4 result 0xffff: must not AV
	.ifdef	DATA_AV
	mov	$r0, [-1]		; syscall convention: data AV on the I/O page
	mov	$r0, 3			; must not execute before the handler
	.else
	mov	$sp, [$pc + (k1200 - .)]
	mov	$pc, $sp		; fetch from page 9: AV
	.endif
kffff:	.word	0xffff
k1200:	.word	0x1200
	.endm

	.macro	page9_code		; logical page 9: never executes
	mov	$r0, 5
	mov	$r1, 5
	mov	[-30], $r0
	mov	$pc, $pc
	.endm

	.if	OFFSET == 0
	.org	USER			; page 8: last page user code may touch
	user_code
	.org	0x1200
	page9_code
	.else
	.org	USER			; decoy: the untranslated address of the user code
	mov	$r0, 5
	.org	0x1200
	page9_code
	.org	USER + (OFFSET << 9)	; where the MMU maps logical page 8
	user_code
	.endif
