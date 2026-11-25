; targets/kernel.asm - the hand-written glue for the bare-metal (kernel) target.
;
; GRUB loads this file, and jumps to _start with the CPU already in 32-bit
; protected mode: interrupts off, flat segments, paging off. From there the
; compiled program takes over. This file is included at the very top of
; glossc's output. It holds only what the bare tongue cannot say: the header
; GRUB looks for, the first instructions, and single-instruction helpers.
;
; Memory map (QEMU is started with -m 128, so everything below 128 MiB exists):
;   0x00100000  this image: header, code, globals          (1 MiB)
;   after it    64 KiB of stack, growing downward
;   0x003F0000  64 KiB scratch the runtime owns (t_scratch)
;   0x00400000  the heap, up to 0x04000000                  (milestone 5)

bits 32                       ; GRUB hands us a 32-bit CPU: assemble i386 code
org 0x00100000                ; the address GRUB will load the image at (1 MiB)

MB_MAGIC equ 0x1BADB002       ; "I am a Multiboot kernel": GRUB looks for this number
MB_FLAGS equ 0x00010003       ; bit 0: align modules; bit 1: give me memory info;
                              ; bit 16: the address fields below are valid, so
                              ; GRUB may load a plain binary - no ELF, no linker

section .text

; ---- Multiboot header: must sit in the first 8 KiB of the file, 4-byte aligned
mb_header:
  dd MB_MAGIC                 ; the magic number
  dd MB_FLAGS                 ; what we ask of the bootloader
  dd (0 - (MB_MAGIC + MB_FLAGS)) & 0xFFFFFFFF   ; checksum: the three words sum to 0
  dd mb_header                ; where this header is, in memory
  dd 0x00100000               ; load the file starting at this address
  dd prog_end                 ; ...up to here (the end of the file's contents)
  dd kstack_top               ; zero everything from there up to here: the stack
  dd _start                   ; start executing here

kstack_top equ prog_end + 0x10000   ; the stack lives in the 64 KiB after the image

; ---- The entry point -----------------------------------------------------
_start:
  cli                         ; no interrupts yet: there is no IDT to catch them
  mov esp, kstack_top         ; a stack, so `call` and `push` work (it grows down)
  mov [mb_info], ebx          ; GRUB passes the address of its info block in ebx
  call g_scroll               ; run the program: every top-level statement, in order
  push 0                      ; if it returns, stop the machine cleanly
  call g_rt_exit

; ---- Single-instruction helpers the language cannot express ---------------
; (called from .glo as `call hlt`, `call cli`, `call sti`, `call load_gdt with ...`)
g_hlt:                        ; sleep until the next interrupt
  hlt
  ret
g_cli:                        ; stop taking interrupts
  cli
  ret
g_sti:                        ; start taking interrupts
  sti
  ret

; ---- load_gdt(base, limit): tell the CPU where our segment table is ---------
; lgdt reads a 6-byte "pseudo-descriptor" from memory: a 16-bit limit, then a
; 32-bit base. Arguments were pushed left to right, so after the call:
;   [esp] = return address   [esp+4] = limit   [esp+8] = base
g_load_gdt:
  mov eax, [esp+8]            ; eax = base address of the table
  mov ecx, [esp+4]            ; ecx = limit (size in bytes minus one)
  mov [gdtr+2], eax           ; the pseudo-descriptor: base goes in bytes 2-5...
  mov [gdtr], cx              ; ...limit in bytes 0-1
  lgdt [gdtr]                 ; load the GDT register
  ; The old segment registers still point into GRUB's table. A far jump
  ; reloads CS with selector 0x08 (our code entry)...
  jmp 0x08:.reload
.reload:
  mov ax, 0x10                ; ...and the others get 0x10, our data entry
  mov ds, ax
  mov es, ax
  mov fs, ax
  mov gs, ax
  mov ss, ax
  ret

; ---- load_idt(base, limit): tell the CPU where the interrupt table is -------
; Same shape as lgdt, but the segment registers are untouched.
g_load_idt:
  mov eax, [esp+8]            ; base
  mov ecx, [esp+4]            ; limit
  mov [idtr+2], eax
  mov [idtr], cx
  lidt [idtr]                 ; load the IDT register
  ret

section .data
mb_info: dd 0                 ; the Multiboot info address GRUB gave us
gdtr: dw 0                    ; pseudo-descriptor for lgdt: limit...
      dd 0                    ; ...and base
idtr: dw 0                    ; pseudo-descriptor for lidt
      dd 0
