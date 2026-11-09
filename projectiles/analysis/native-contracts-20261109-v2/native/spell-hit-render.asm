2356b0: push rbp
2356b2: push rsi
2356b3: lea rbp, [rsp - 0x4f]
2356b8: sub rsp, 0xa8
2356bf: mov rax, qword ptr [rip + 0x42f312] ; b'2\xa2\xdf-\x99+'
2356c6: xor rax, rsp
2356c9: mov qword ptr [rbp + 0x27], rax
2356cd: mov r9, qword ptr [rcx + 0x18]
2356d1: mov rsi, rcx
2356d4: test r9, r9
2356d7: je 0x2359ee
2356dd: mov r11d, dword ptr [rcx + 0xc]
2356e1: mov eax, dword ptr [rsi + 0x10]
2356e4: movzx ecx, byte ptr [rip + 0x369500] ; b' \x0f'
2356eb: cdq 
2356ec: idiv ecx
2356ee: movsx ecx, word ptr [r9 + 0xbbc]
2356f6: movsx r8d, ax
2356fa: mov eax, r11d
2356fd: imul r8d, ecx
235701: cdq 
235702: movzx ecx, byte ptr [rip + 0x3694e1] ; b'  \x0f'
235709: idiv ecx
23570b: mov qword ptr [rsp + 0x98], r14
235713: lea r14, [r9 + 0x5c8]
23571a: add ax, r8w
23571e: movsx rax, ax
235722: test eax, eax
235724: js 0x2359e6
23572a: cmp eax, dword ptr [r9 + 0xbb8]
235731: jge 0x2359e6
235737: mov rcx, rax
23573a: mov rax, qword ptr [r9 + 0xbb0]
235741: movzx ecx, word ptr [rax + rcx*2]
235745: test word ptr [rip + 0x36949c], cx ; b'\xff\x7f  \x0f'
23574c: je 0x2359e6
235752: movzx r8d, byte ptr [rsi + 0x28]
235757: lea rdx, [rsi + 0xc]
23575b: mov qword ptr [rsp + 0xc8], rbx
235763: mov rcx, r9
235766: mov ebx, dword ptr [r14 + 0x78]
23576a: mov qword ptr [rsp + 0xd0], rdi
235772: mov edi, dword ptr [r14 + 0x80]
235779: mov qword ptr [rsp + 0xd8], r12
235781: mov r12d, dword ptr [r14 + 0x84]
235788: sub r12d, dword ptr [r14 + 0x7c]
23578c: mov qword ptr [rsp + 0xa0], r13
235794: mov r13d, dword ptr [r14 + 0xc0]
23579b: mov qword ptr [rsp + 0x90], r15
2357a3: mov r15d, dword ptr [r14 + 0xc4]
2357aa: add r12d, r15d
2357ad: mov dword ptr [rbp - 0x11], r11d
2357b1: call 0x180c10
2357b6: mov ecx, dword ptr [rsi + 0x10]
2357b9: lea rdx, [rbp - 0x19]
2357bd: sub ecx, dword ptr [rsi + 0x14]
2357c0: add eax, ecx
2357c2: lea rcx, [rsi + 0x1b8]
2357c9: mov dword ptr [rbp - 0xd], eax
2357cc: call 0x411660
2357d1: lea rdx, [rbp - 9]
2357d5: lea rcx, [rsi + 0x1b8]
2357dc: call 0x411780
2357e1: mov ecx, dword ptr [rbp - 5]
2357e4: xor eax, eax
2357e6: mov edx, dword ptr [rbp - 0xd]
2357e9: sub edx, dword ptr [rbp - 0x15]
2357ec: mov r10d, dword ptr [rbp - 0x11]
2357f0: sub r10d, dword ptr [rbp - 0x19]
2357f4: mov dword ptr [rbp + 0x13], ecx
2357f7: lea r8d, [rdx + rcx]
2357fb: mov qword ptr [rbp + 7], rax
2357ff: mov rax, qword ptr [rbp - 9]
235803: mov ecx, r13d
235806: sub ecx, ebx
235808: mov dword ptr [rbp + 0xf], eax
23580b: add ecx, edi
23580d: mov dword ptr [rbp + 0x17], r10d
235811: mov dword ptr [rbp + 0x1b], edx
235814: mov dword ptr [rbp + 0x23], r8d
235818: lea r9d, [r10 + rax]
23581c: mov dword ptr [rbp + 0x1f], r9d
235820: cmp r10d, ecx
235823: jge 0x2359be
235829: cmp r9d, r13d
23582c: jl 0x2359be
235832: cmp edx, r12d
235835: jge 0x2359be
23583b: cmp r8d, r15d
23583e: jl 0x2359be
235844: cmp r10d, r13d
235847: cmovge r13d, r10d
23584b: cmp ecx, r9d
23584e: cmovge ecx, r9d
235852: cmp edx, r15d
235855: cmovge r15d, edx
235859: cmp r12d, r8d
23585c: cmovge r12d, r8d
235860: cmp ecx, r13d
235863: jle 0x2359be
235869: cmp r12d, r15d
23586c: jle 0x2359be
235872: mov ecx, dword ptr [rsi + 0x410]
235878: lea r9, [rbp - 0x11]
23587c: mov r8d, dword ptr [rip + 0x36cac5] ; b''
235883: lea rdx, [rbp + 7]
235887: and r8d, 0xfffffff7
23588b: mov eax, ecx
23588d: or eax, dword ptr [rip + 0x36cab1] ; b'\x80'
235893: or r8d, 1
235897: test ecx, ecx
235899: mov rcx, r14
23589c: cmovne r8d, eax
2358a0: lea rax, [rbp - 0x19]
2358a4: mov qword ptr [rsp + 0x20], rax
2358a9: mov dword ptr [rsi + 0x410], r8d
2358b0: call 0x29e1b0
2358b5: mov r8d, dword ptr [rsi + 0x410]
2358bc: lea rdx, [rbp + 7]
2358c0: mov rcx, r14
2358c3: call 0x29e190
2358c8: test eax, eax
2358ca: je 0x2359be
2358d0: cmp byte ptr [rsi + 0x414], 0
2358d7: je 0x235918
2358d9: mov rcx, qword ptr [rsi + 0x3f0]
2358e0: call 0x3f6d50
2358e5: mov rbx, qword ptr [rsi + 0x3f0]
2358ec: mov rcx, rbx
2358ef: call 0x3f7890
2358f4: mov rcx, rbx
2358f7: mov edi, eax
2358f9: call 0x3f78b0
2358fe: movzx r9d, word ptr [rip + 0x38ad72] ; b''
235906: lea rcx, [rsi + 0x1b8]
23590d: mov rdx, rax
235910: mov r8d, edi
235913: call 0x4123c0
235918: movzx eax, byte ptr [rsi + 0x415]
23591f: lea rdx, [rsi + 0x1b8]
235926: mov r9d, dword ptr [rbp - 0x15]
23592a: mov rcx, r14
23592d: mov r8d, dword ptr [rbp - 0x19]
235931: mov dword ptr [rsp + 0x28], eax
235935: mov eax, dword ptr [rsi + 0x410]
23593b: mov dword ptr [rsp + 0x20], eax
23593f: call 0x29e260
235944: mov eax, dword ptr [rsi + 0x410]
23594a: xor r9d, r9d
23594d: mov r8d, dword ptr [rbp - 0xd]
235951: mov rcx, r14
235954: mov edx, dword ptr [rbp - 0x11]
235957: mov dword ptr [rsp + 0x38], eax
23595b: lea rax, [rbp + 0x17]
23595f: mov byte ptr [rsp + 0x30], 0
235964: mov qword ptr [rsp + 0x28], rax
235969: lea rax, [rbp - 0x19]
23596d: mov qword ptr [rsp + 0x20], rax
235972: call 0x29e4c0
235977: mov edx, dword ptr [rsi + 0x410]
23597d: lea r9, [rbp - 1]
235981: xor eax, eax
235983: xor r8d, r8d
235986: mov rcx, r14
235989: mov qword ptr [rbp - 1], rax
23598d: call 0x29ea40
235992: mov eax, dword ptr [rsi + 0x410]
235998: lea rdx, [rbp + 7]
23599c: mov r9d, dword ptr [rbp - 0xd]
2359a0: mov rcx, r14
2359a3: mov r8d, dword ptr [rbp - 0x11]
2359a7: mov dword ptr [rsp + 0x30], eax
2359ab: mov eax, dword ptr [rbp - 0x15]
2359ae: mov dword ptr [rsp + 0x28], eax
2359b2: mov eax, dword ptr [rbp - 0x19]
2359b5: mov dword ptr [rsp + 0x20], eax
2359b9: call 0x29df60
2359be: mov rbx, qword ptr [rsp + 0xc8]
2359c6: mov r13, qword ptr [rsp + 0xa0]
2359ce: mov r12, qword ptr [rsp + 0xd8]
2359d6: mov rdi, qword ptr [rsp + 0xd0]
2359de: mov r15, qword ptr [rsp + 0x90]
2359e6: mov r14, qword ptr [rsp + 0x98]
2359ee: mov rcx, qword ptr [rbp + 0x27]
2359f2: xor rcx, rsp
2359f5: call 0x4f77a0
2359fa: add rsp, 0xa8
235a01: pop rsi
235a02: pop rbp
235a03: ret 
235a04: int3 
235a05: int3 
235a06: int3 
235a07: int3 
235a08: int3 
235a09: int3 
235a0a: int3 
235a0b: int3 
235a0c: int3 
235a0d: int3 
235a0e: int3 
235a0f: int3 
235a10: mov r11, rsp
235a13: push rbp
235a14: push r14
235a16: lea rbp, [r11 - 0x5f]
235a1a: sub rsp, 0xa8
235a21: mov rax, qword ptr [rip + 0x42efb0] ; b'2\xa2\xdf-\x99+'
235a28: xor rax, rsp
235a2b: mov qword ptr [rbp + 0x27], rax
235a2f: mov r9, qword ptr [rcx + 0x18]
235a33: mov r14, rcx
235a36: test r9, r9
235a39: je 0x235d31
235a3f: .byte 0x41
