; targets/linux.asm - the hand-written glue for the Linux i386 target.
;
; Everything the bare tongue cannot say itself lives here: the file header
; Linux wants, the entry point, and the one instruction that asks the kernel
; for something (int 0x80). It is included at the very top of glossc's
; output, so it is the first thing in the file.
;
; Memory map (one RWX segment; Linux zero-fills what the file does not hold):
;   0x08048000  this file: ELF header, code, then globals
;   0x08100000  1 MiB of scratch RAM for programs that inscribe/peek
;   0x08200000  64 KiB owned by the runtime (t_scratch)
;   0x08210000  256 KiB of I/O port latches (see SPEC-BARE.md section 3.3)
;   after that  the heap, which the runtime grows with the brk system call

bits 32                       ; the CPU is in 32-bit protected mode: assemble i386 code
org 0x08048000                ; the address Linux will load this file at

t_ports equ 0x08210000        ; where the port latches live (used by compiled whisper/listen)

section .text

; ---- ELF header (52 bytes): "I am a 32-bit executable for i386" ------------
ehdr:
  db 0x7f, 'E', 'L', 'F'      ; magic number: every ELF file starts with these four bytes
  db 1                        ; 32-bit objects
  db 1                        ; little-endian
  db 1                        ; ELF version 1
  times 9 db 0                ; padding up to byte 16 (OS ABI, unused)
  dw 2                        ; type: executable
  dw 3                        ; machine: Intel 80386
  dd 1                        ; ELF version again
  dd _start                   ; entry point: where to start running
  dd phdr - $$                ; where the program header table sits in the file
  dd 0                        ; section header table: none needed to run
  dd 0                        ; flags: none for i386
  dw 52                       ; size of this header
  dw 32                       ; size of one program header
  dw 1                        ; how many program headers
  dw 0, 0, 0                  ; section header size/count/names: none

; ---- Program header (32 bytes): "map this file into memory like so" ----------
phdr:
  dd 1                        ; type PT_LOAD: load this part of the file
  dd 0                        ; from file offset 0 (the whole file, header included)
  dd $$                       ; to this virtual address...
  dd $$                       ; ...and this physical one (ignored on Linux)
  dd prog_end - $$            ; this many bytes come from the file
  dd 0x10000000               ; but reserve 256 MiB in memory (the heap lives past 0x08400000); the rest starts as zeros
  dd 7                        ; permissions: readable, writable, executable
  dd 0x1000                   ; alignment: one page

; ---- The entry point ------------------------------------------------------
_start:
  mov [0x08200800], esp       ; remember the initial stack: argc and argv live there (heed)
  call g_scroll              ; run the program: every top-level statement, in order
  push 0                      ; then leave with status 0 (one argument for rt_exit)
  call g_rt_exit

; ---- syscall(nr, a, b, c): the one instruction the language cannot express --
; The Linux system-call convention is: number in eax, arguments in ebx, ecx,
; edx, then `int 0x80` traps into the kernel, which answers in eax.
; Our own convention pushes arguments left to right, so after `push ebx`:
;   [esp]=saved ebx  [esp+4]=return  [esp+8]=c  [esp+12]=b  [esp+16]=a  [esp+20]=nr
g_syscall:
  push ebx                    ; ebx belongs to our caller; Linux wants to use it
  mov eax, [esp+20]           ; eax = nr, which system call
  mov ebx, [esp+16]           ; ebx = a, first argument
  mov ecx, [esp+12]           ; ecx = b, second argument
  mov edx, [esp+8]            ; edx = c, third argument
  int 0x80                    ; ask the kernel; the answer comes back in eax
  pop ebx                     ; give ebx back
  ret                         ; return to the caller (who removes the arguments)
