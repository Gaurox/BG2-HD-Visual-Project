307df6: lea rax, [rip + 0x2a16d3]
307dfd: lea r15, [rbx + 0xce8]
307e04: mov qword ptr [rbx], rax
307e07: mov rcx, r15
307e0a: call 0x140410f70
307e0f: lea r12, [rbx + 0xe20]
307e16: mov rcx, r12
307e19: call 0x140410f70
307e1e: movzx edx, word ptr [rip + 0x2b8857]
307e25: lea rcx, [rbx + 0xf58]
307e2c: call 0x140421010
307e31: mov word ptr [rbx + 8], r14w
307e36: lea rcx, [rip + 0x2a33bb]
307e3d: mov qword ptr [rbx + 0xf8c], 1
307e48: mov edx, r14d
307e4b: mov word ptr [rbx + 0xa], 0
307e51: mov edi, r14d
307e54: mov dword ptr [rbx + 0x30], 0xa0000
307e5b: mov dword ptr [rbx + 0x34], 0xafff6
307e62: mov dword ptr [rbx + 0x38], 0xfff6
307e69: mov dword ptr [rbx + 0x3c], 0xfff6fff6
307e70: mov dword ptr [rbx + 0x40], 0xfff60000
307e77: mov dword ptr [rbx + 0x44], 0xfff6000a
307e7e: mov dword ptr [rbx + 0x48], 0xa
307e85: mov dword ptr [rbx + 0x4c], 0xa000a
307e8c: call 0x140400170
307e91: mov rdx, rax
307e94: lea rcx, [rsp + 0x28]
307e99: call 0x1403ff7c0
307e9e: mov rcx, rbx
307ea1: mov rdx, qword ptr [rax]
307ea4: call 0x14033ec40
307ea9: test al, al
307eab: jne 0x1403080b2
307eb1: mov rax, qword ptr [rip + 0x354c58]
307eb8: and edi, 0xf00
307ebe: mov qword ptr [rsp + 0x20], rax
307ec3: cmp edi, 0x400
307ec9: ja 0x140307fab
307ecf: je 0x140307f8e
307ed5: test edi, edi
307ed7: je 0x140307f58
307ed9: cmp edi, 0x100
307edf: je 0x140307f4f
307ee1: cmp edi, 0x200
307ee7: je 0x140307f2f
307ee9: cmp edi, 0x300
307eef: jne 0x14030800c
307ef5: test r14b, 0xf0
307ef9: mov dword ptr [rbx + 0xf90], 1
307f03: lea rax, [rip + 0x2a3656]
307f0a: lea rdx, [rip + 0x2a3647]
307f11: cmovne rdx, rax
307f15: lea rcx, [rsp + 0x20]
307f1a: call 0x1403fd810
307f1f: lea rax, [rip + 0x2a3642]
307f26: mov qword ptr [rbx + 0x28], rax
307f2a: jmp 0x14030800c
307f2f: test r14b, 0xf0
307f33: lea rax, [rip + 0x2a3616]
307f3a: lea rdx, [rip + 0x2a3607]
307f41: cmovne rdx, rax
307f45: lea rcx, [rsp + 0x20]
307f4a: jmp 0x140308007
307f4f: lea rdx, [rip + 0x2a35ea]
307f56: jmp 0x140307f5f
307f58: lea rdx, [rip + 0x2a35cd]
307f5f: lea rcx, [rsp + 0x20]
307f64: mov byte ptr [rbx + 0x22], 0xff
307f68: call 0x1403fd810
307f6d: xor r14d, r14d
307f70: mov byte ptr [rbx + 0x5f0], 5
307f77: lea rax, [rip + 0x2a35ba]
307f7e: mov dword ptr [rbx + 0xf8c], r14d
307f85: mov qword ptr [rbx + 0x28], rax
307f89: jmp 0x14030800f
307f8e: test r14b, 0xf0
307f92: lea rax, [rip + 0x2a35df]
307f99: lea rdx, [rip + 0x2a35d0]
307fa0: cmovne rdx, rax
307fa4: lea rcx, [rsp + 0x20]
307fa9: jmp 0x140308007
307fab: cmp edi, 0x500
307fb1: je 0x140307fee
307fb3: cmp edi, 0x600
307fb9: je 0x140307fd1
307fbb: cmp edi, 0x700
307fc1: jne 0x14030800c
307fc3: lea rdx, [rip + 0x2a35d6]
307fca: lea rcx, [rsp + 0x20]
307fcf: jmp 0x140308007
307fd1: test r14b, 0xf0
307fd5: lea rax, [rip + 0x2a35bc]
307fdc: lea rdx, [rip + 0x2a35ad]
307fe3: cmovne rdx, rax
307fe7: lea rcx, [rsp + 0x20]
307fec: jmp 0x140308007
307fee: lea rcx, [rsp + 0x20]
307ff3: lea rdx, [rip + 0x2a3586]
307ffa: test r14b, 0xf0
307ffe: je 0x140308007
308000: lea rdx, [rip + 0x2a3581]
308007: call 0x1403fd810
30800c: xor r14d, r14d
30800f: lea r8, [rip + 0x2a3482]
308016: lea rdx, [rsp + 0x20]
30801b: lea rcx, [rsp + 0x28]
308020: call 0x1403fd8e0
308025: mov rdx, rax
308028: lea rcx, [rsp + 0x30]
30802d: call 0x1403ff710
308032: mov r9d, 1
308038: lea rcx, [rbx + 0xdf0]
30803f: mov r8d, r9d
308042: lea rdx, [rsp + 0x30]
308047: call 0x14014d080
30804c: lea rcx, [rsp + 0x28]
308051: call 0x1403fd740
308056: cmp dword ptr [rip + 0x407cbb], 0
30805d: jne 0x1403080a6
30805f: lea r8, [rip + 0x2a3542]
308066: lea rdx, [rsp + 0x20]
30806b: lea rcx, [rsp + 0x30]
308070: call 0x1403fd8e0
308075: mov rdx, rax
308078: lea rcx, [rsp + 0x28]
30807d: call 0x1403ff710
308082: mov r9d, 1
308088: lea rcx, [rbx + 0xf28]
30808f: mov r8d, r9d
308092: lea rdx, [rsp + 0x28]
308097: call 0x14014d080
30809c: lea rcx, [rsp + 0x30]
3080a1: call 0x1403fd740
3080a6: lea rcx, [rsp + 0x20]
3080ab: call 0x1403fd740
3080b0: jmp 0x1403080b5
3080b2: xor r14d, r14d
3080b5: mov rcx, rbx
3080b8: call 0x140316900
3080bd: mov rax, qword ptr [rip + 0x35f484]
3080c4: mov rcx, qword ptr [rax + 0x1090]
3080cb: cmp dword ptr [rcx + 0x7cd0], 0
3080d2: je 0x1403080db
3080d4: mov dword ptr [rbx + 0xf90], r14d
3080db: cmp dword ptr [rbx + 0xf8c], 0
3080e2: mov qword ptr [rbx + 0xcd8], r15
3080e9: mov qword ptr [rbx + 0xce0], r12
3080f0: mov qword ptr [rbx + 0xcd0], r15
3080f7: je 0x14030815d
3080f9: xor dil, dil
3080fc: nop dword ptr [rax]
308100: mov rax, qword ptr [rip + 0x35f441]
308107: lea rcx, [rbx + 0xf58]
30810e: movzx r8d, byte ptr [rsi]
308112: movzx edx, dil
308116: mov r9, qword ptr [rax + 0x1090]
30811d: add r9, 0x63d8
308124: call 0x1404221c0
308129: inc dil
30812c: lea rsi, [rsi + 1]
308130: cmp dil, 7
308134: jb 0x140308100
308136: lea rdx, [rbx + 0xf58]
30813d: mov rcx, r15
308140: call 0x140412390
308145: cmp dword ptr [rip + 0x407bcc], 0
30814c: jne 0x14030815d
30814e: lea rdx, [rbx + 0xf58]
308155: mov rcx, r12
308158: call 0x140412390
30815d: mov word ptr [rbx + 0xf88], r14w
308165: cmp dword ptr [rip + 0x407bac], 0
30816c: je 0x14030819f
30816e: cmp dword ptr [rbx + 0xf8c], 0
308175: je 0x140308198
308177: movzx r8d, byte ptr [rip + 0x2b84fb]
30817f: lea rdx, [rsp + 0x20]
308184: mov r9d, 0xff00
30818a: lea rcx, [rbx + 0xf58]
308191: call 0x140422180
308196: jmp 0x14030819f
308198: mov byte ptr [rbx + 0xe18], 0
30819f: movzx eax, byte ptr [rip + 0x2a4d04]
3081a6: mov byte ptr [rbx + 0xf94], al
3081ac: mov word ptr [rbx + 0xf8a], r13w
3081b4: cmp dword ptr [rip + 0x407b5d], 0
3081bb: jne 0x1403081cf
3081bd: movzx ecx, al
3081c0: cmp r13w, cx
3081c4: jle 0x1403081cf
3081c6: mov r8, qword ptr [rbx + 0xce0]
3081cd: jmp 0x1403081d6
3081cf: mov r8, qword ptr [rbx + 0xcd8]
3081d6: mov qword ptr [rbx + 0xcd0], r8
3081dd: cmp dword ptr [rip + 0x407b34], 0
3081e4: je 0x140308222
3081e6: movsx ecx, word ptr [rbx + 0xf8a]
3081ed: movzx eax, byte ptr [rbx + 0xf94]
3081f4: cmp ecx, eax
3081f6: jle 0x140308222
3081f8: mov eax, 0xf
3081fd: sub eax, ecx
3081ff: and eax, 0x8000000f
308204: jge 0x14030820d
308206: dec eax
308208: or eax, 0xfffffff0
30820b: inc eax
30820d: movzx ecx, word ptr [rbx + 0xf88]
308214: cdq 
308215: sub eax, edx
308217: shl cx, 3
30821b: sar eax, 1
30821d: add ax, cx
308220: jmp 0x14030823c
308222: movsx eax, word ptr [rbx + 0xf8a]
308229: cdq 
30822a: sub eax, edx
30822c: movzx edx, word ptr [rbx + 0xf88]
308233: shl dx, 3
308237: sar eax, 1
308239: add ax, dx
30823c: movzx edx, ax
30823f: mov rcx, r8
308242: call 0x140412380
308247: mov rax, rbx
30824a: mov rcx, qword ptr [rsp + 0x38]
30824f: xor rcx, rsp
308252: call 0x1404f77a0
308257: mov rbx, qword ptr [rsp + 0x98]
30825f: add rsp, 0x40
308263: pop r15
308265: pop r14
308267: pop r13
308269: pop r12
30826b: pop rdi
30826c: pop rsi
30826d: pop rbp
30826e: ret 