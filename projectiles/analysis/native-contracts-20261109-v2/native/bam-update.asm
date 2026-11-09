228650: push rbp
228652: push rdi
228653: lea rbp, [rsp - 0x4f]
228658: sub rsp, 0xd8
22865f: mov rax, qword ptr [rip + 0x43c372] ; b'2\xa2\xdf-\x99+'
228666: xor rax, rsp
228669: mov qword ptr [rbp + 0x27], rax
22866d: mov rax, qword ptr [rip + 0x43eed4] ; b''
228674: mov rdi, rcx
228677: mov rcx, qword ptr [rax + 0x1090]
22867e: cmp dword ptr [rcx + 0x9690], 0
228685: je 0x228696
228687: mov eax, dword ptr [rdi + 0x48]
22868a: cmp dword ptr [rcx + 0x9694], eax
228690: jne 0x228e47
228696: mov rax, qword ptr [rdi + 0xc]
22869a: mov qword ptr [rsp + 0xf8], rbx
2286a2: mov qword ptr [rsp + 0xd0], r13
2286aa: mov r13d, 1
2286b0: mov qword ptr [rbp - 9], rax
2286b4: mov eax, dword ptr [rdi + 0x188]
2286ba: mov qword ptr [rsp + 0xc8], r14
2286c2: bt eax, 0x11
2286c6: jae 0x228762
2286cc: mov ebx, r13d
2286cf: test al, al
2286d1: jns 0x2286ed
2286d3: mov rcx, qword ptr [rdi + 0x1b8]
2286da: call 0x411af0
2286df: movzx ecx, ax
2286e2: mov eax, 0xaaaaaaab
2286e7: mul ecx
2286e9: mov ebx, edx
2286eb: shr ebx, 1
2286ed: cmp word ptr [rdi + 0x184], 0
2286f5: mov r8, qword ptr [rdi + 0x1b8]
2286fc: jg 0x22874a
2286fe: mov word ptr [rdi + 0x184], r13w
228706: lea eax, [rbx + rbx]
228709: movzx ecx, word ptr [r8 + 0x11a]
228711: cmp ecx, eax
228713: mov rcx, r8
228716: je 0x228730
228718: lea edx, [rbx + rbx]
22871b: call 0x412380
228720: mov rcx, qword ptr [rdi + 0x1b8]
228727: xor edx, edx
228729: call 0x411610
22872e: jmp 0x22876e
228730: call 0x411df0
228735: test eax, eax
228737: je 0x228762
228739: mov rax, qword ptr [rdi]
22873c: mov rcx, rdi
22873f: call qword ptr [rax + 0xe0]
228745: jmp 0x228e2f
22874a: mov rcx, r8
22874d: call 0x411df0
228752: mov rcx, qword ptr [rdi + 0x1b8]
228759: test eax, eax
22875b: je 0x228769
22875d: movzx edx, bx
228760: jmp 0x22871b
228762: mov rcx, qword ptr [rdi + 0x1b8]
228769: mov rax, qword ptr [rcx]
22876c: call qword ptr [rax]
22876e: cmp dword ptr [rdi + 0x210], 0
228775: mov qword ptr [rsp + 0x108], r12
22877d: je 0x22878b
22877f: mov rcx, qword ptr [rdi + 0x1c0]
228786: mov rax, qword ptr [rcx]
228789: call qword ptr [rax]
22878b: xor r12d, r12d
22878e: mov qword ptr [rsp + 0x100], rsi
228796: cmp dword ptr [rdi + 0x344], r12d
22879d: je 0x228b10
2287a3: lea rdx, [rip + 0x3c3003] ; b''
2287aa: mov qword ptr [rbp - 1], r12
2287ae: lea rcx, [rbp - 0x11]
2287b2: call 0x3fd6b0
2287b7: movzx ecx, byte ptr [rdi + 0x350]
2287be: lea eax, [rcx + 1]
2287c1: mov byte ptr [rdi + 0x350], al
2287c7: cmp cl, byte ptr [rdi + 0x348]
2287cd: jne 0x228b07
2287d3: mov ecx, 0xd0
2287d8: mov qword ptr [rsp + 0xc0], r15
2287e0: mov byte ptr [rdi + 0x350], r12b
2287e7: call 0x4f7a88
2287ec: mov rsi, rax
2287ef: test rax, rax
2287f2: je 0x2288eb
2287f8: call 0x50933c
2287fd: and eax, 0x7fff
228802: lea ebx, [rax + rax*4]
228805: sar ebx, 0xf
228808: call 0x50933c
22880d: movsx r9d, word ptr [rip + 0x384707] ; b'\n'
228815: lea r15, [rdi + 0x349]
22881c: mov edx, dword ptr [rdi + 0xd4]
228822: and eax, 0x7fff
228827: mov r8d, dword ptr [rdi + 0xc]
22882b: add r8d, -2
22882f: shl edx, 2
228832: lea ecx, [rax + rax*4]
228835: mov eax, 0x55555556
22883a: imul edx
22883c: sar ecx, 0xf
22883f: add r8d, ecx
228842: mov eax, edx
228844: shr eax, 0x1f
228847: mov ecx, r9d
22884a: add edx, eax
22884c: shl r8d, cl
22884f: sub r8d, edx
228852: mov eax, 0x55555556
228857: mov dword ptr [rbp - 0x19], r8d
22885b: mov r9, r15
22885e: mov r8d, dword ptr [rdi + 0x10]
228862: add r8d, -2
228866: add r8d, ebx
228869: shl r8d, cl
22886c: mov ecx, dword ptr [rdi + 0xd8]
228872: shl ecx, 2
228875: imul ecx
228877: mov ecx, dword ptr [rdi + 0x14]
22887a: mov eax, edx
22887c: neg ecx
22887e: shr eax, 0x1f
228881: add edx, eax
228883: movzx eax, byte ptr [rdi + 0x62]
228887: mov byte ptr [rsp + 0x68], al
22888b: sub r8d, edx
22888e: movzx eax, byte ptr [rip + 0x3845cc] ; b'\x01\x02\x01\x02'
228895: movzx edx, word ptr [rdi + 0x352]
22889c: mov dword ptr [rsp + 0x60], r12d
2288a1: mov byte ptr [rsp + 0x58], al
2288a5: lea rax, [rbp - 1]
2288a9: mov byte ptr [rsp + 0x50], r12b
2288ae: mov word ptr [rsp + 0x48], r12w
2288b4: mov qword ptr [rsp + 0x40], rax
2288b9: lea rax, [rbp - 0x19]
2288bd: mov dword ptr [rsp + 0x38], ecx
2288c1: mov rcx, rsi
2288c4: mov qword ptr [rsp + 0x30], rax
2288c9: mov rax, qword ptr [rdi + 0x18]
2288cd: mov qword ptr [rsp + 0x28], rax
2288d2: lea rax, [rbp - 0x11]
2288d6: mov dword ptr [rbp - 0x15], r8d
2288da: movzx r8d, word ptr [rdi + 0x60]
2288df: mov qword ptr [rsp + 0x20], rax
2288e4: call 0x3438b0
2288e9: jmp 0x2288f5
2288eb: mov rax, r12
2288ee: lea r15, [rdi + 0x349]
2288f5: test byte ptr [rdi + 0x16c], 0x40
2288fc: je 0x228905
2288fe: mov dword ptr [rax + 0xc4], r13d
228905: mov ecx, 0xd0
22890a: call 0x4f7a88
22890f: mov rsi, rax
228912: test rax, rax
228915: je 0x2289d7
22891b: call 0x50933c
228920: and eax, 0x7fff
228925: lea ebx, [rax + rax*4]
228928: sar ebx, 0xf
22892b: call 0x50933c
228930: movsx ecx, word ptr [rip + 0x3845e5] ; b'\n'
228937: and eax, 0x7fff
22893c: mov r8d, dword ptr [rdi + 0xc]
228940: mov r9, r15
228943: add r8d, -2
228947: lea edx, [rax + rax*4]
22894a: movzx eax, byte ptr [rdi + 0x62]
22894e: mov byte ptr [rsp + 0x68], al
228952: movzx eax, byte ptr [rip + 0x384508] ; b'\x01\x02\x01\x02'
228959: sar edx, 0xf
22895c: add r8d, edx
22895f: mov dword ptr [rsp + 0x60], r12d
228964: mov edx, dword ptr [rdi + 0x10]
228967: mov byte ptr [rsp + 0x58], al
22896b: add edx, -2
22896e: shl r8d, cl
228971: lea rax, [rbp - 1]
228975: sub r8d, dword ptr [rdi + 0xd4]
22897c: add edx, ebx
22897e: shl edx, cl
228980: mov ecx, dword ptr [rdi + 0x14]
228983: sub edx, dword ptr [rdi + 0xd8]
228989: neg ecx
22898b: mov byte ptr [rsp + 0x50], r12b
228990: mov word ptr [rsp + 0x48], r12w
228996: mov qword ptr [rsp + 0x40], rax
22899b: lea rax, [rbp - 0x19]
22899f: mov dword ptr [rsp + 0x38], ecx
2289a3: mov rcx, rsi
2289a6: mov qword ptr [rsp + 0x30], rax
2289ab: mov rax, qword ptr [rdi + 0x18]
2289af: mov qword ptr [rsp + 0x28], rax
2289b4: lea rax, [rbp - 0x11]
2289b8: mov dword ptr [rbp - 0x19], r8d
2289bc: movzx r8d, word ptr [rdi + 0x60]
2289c1: mov dword ptr [rbp - 0x15], edx
2289c4: movzx edx, word ptr [rdi + 0x352]
2289cb: mov qword ptr [rsp + 0x20], rax
2289d0: call 0x3438b0
2289d5: jmp 0x2289da
2289d7: mov rax, r12
2289da: test byte ptr [rdi + 0x16c], 0x40
2289e1: je 0x2289ea
2289e3: mov dword ptr [rax + 0xc4], r13d
2289ea: mov ecx, 0xd0
2289ef: call 0x4f7a88
2289f4: mov rsi, rax
2289f7: test rax, rax
2289fa: je 0x228aec
228a00: call 0x50933c
228a05: and eax, 0x7fff
228a0a: lea ebx, [rax + rax*4]
228a0d: sar ebx, 0xf
228a10: call 0x50933c
228a15: mov r9d, dword ptr [rdi + 0xc]
228a19: and eax, 0x7fff
228a1e: mov edx, dword ptr [rdi + 0xd4]
228a24: add r9d, -2
228a28: movsx r10d, word ptr [rip + 0x3844ec] ; b'\n'
228a30: add edx, edx
228a32: lea ecx, [rax + rax*4]
228a35: mov eax, 0x55555556
228a3a: imul edx
228a3c: sar ecx, 0xf
228a3f: mov eax, 0x55555556
228a44: add r9d, ecx
228a47: mov r8d, edx
228a4a: shr edx, 0x1f
228a4d: mov ecx, r10d
228a50: add r8d, edx
228a53: shl r9d, cl
228a56: sub r9d, r8d
228a59: mov r8d, dword ptr [rdi + 0x10]
228a5d: add r8d, -2
228a61: mov dword ptr [rbp - 0x19], r9d
228a65: add r8d, ebx
228a68: mov r9, r15
228a6b: shl r8d, cl
228a6e: mov ecx, dword ptr [rdi + 0xd8]
228a74: add ecx, ecx
228a76: imul ecx
228a78: mov ecx, dword ptr [rdi + 0x14]
228a7b: mov eax, edx
228a7d: neg ecx
228a7f: shr eax, 0x1f
228a82: add edx, eax
228a84: movzx eax, byte ptr [rdi + 0x62]
228a88: mov byte ptr [rsp + 0x68], al
228a8c: sub r8d, edx
228a8f: movzx eax, byte ptr [rip + 0x3843cb] ; b'\x01\x02\x01\x02'
228a96: movzx edx, word ptr [rdi + 0x352]
228a9d: mov dword ptr [rsp + 0x60], r12d
228aa2: mov byte ptr [rsp + 0x58], al
228aa6: lea rax, [rbp - 1]
228aaa: mov byte ptr [rsp + 0x50], r12b
228aaf: mov word ptr [rsp + 0x48], r12w
228ab5: mov qword ptr [rsp + 0x40], rax
228aba: lea rax, [rbp - 0x19]
228abe: mov dword ptr [rsp + 0x38], ecx
228ac2: mov rcx, rsi
228ac5: mov qword ptr [rsp + 0x30], rax
228aca: mov rax, qword ptr [rdi + 0x18]
228ace: mov qword ptr [rsp + 0x28], rax
228ad3: lea rax, [rbp - 0x11]
228ad7: mov dword ptr [rbp - 0x15], r8d
228adb: movzx r8d, word ptr [rdi + 0x60]
228ae0: mov qword ptr [rsp + 0x20], rax
228ae5: call 0x3438b0
228aea: jmp 0x228aef
228aec: mov rax, r12
228aef: test byte ptr [rdi + 0x16c], 0x40
228af6: mov r15, qword ptr [rsp + 0xc0]
228afe: je 0x228b07
228b00: mov dword ptr [rax + 0xc4], r13d
228b07: lea rcx, [rbp - 0x11]
228b0b: call 0x3fd740
228b10: test byte ptr [rdi + 0x16c], 0x80
228b17: jne 0x228b2f
228b19: movzx ecx, word ptr [rdi + 0x184]
228b20: lea eax, [rcx - 1]
228b23: mov word ptr [rdi + 0x184], ax
228b2a: test cx, cx
228b2d: je 0x228b48
228b2f: test byte ptr [rdi + 0x188], 2
228b36: je 0x228b59
228b38: mov rcx, rdi
228b3b: call 0x22b000
228b40: test al, al
228b42: je 0x228e1f
228b48: mov rax, qword ptr [rdi]
228b4b: mov rcx, rdi
228b4e: call qword ptr [rax + 0xe0]
228b54: jmp 0x228e1f
228b59: mov edx, dword ptr [rdi + 0xfc]
228b5f: mov eax, edx
228b61: sub eax, dword ptr [rdi + 0x10]
228b64: mov r8d, dword ptr [rdi + 0xf8]
228b6b: mov esi, r8d
228b6e: sub esi, dword ptr [rdi + 0xc]
228b71: movsx ecx, word ptr [rdi + 0x64]
228b75: imul eax, eax
228b78: imul esi, esi
228b7b: add esi, eax
228b7d: lea eax, [rcx + 1]
228b80: imul eax, eax
228b83: cmp esi, eax
228b85: jg 0x228b9f
228b87: mov dword ptr [rdi + 0xc], r8d
228b8b: mov dword ptr [rdi + 0x10], edx
228b8e: mov rax, qword ptr [rdi]
228b91: mov rcx, rdi
228b94: call qword ptr [rax + 0xd8]
228b9a: jmp 0x228e1f
228b9f: cmp dword ptr [rdi + 0x160], r12d
228ba6: je 0x228b8e
228ba8: mov eax, dword ptr [rdi + 0x6c]
228bab: cmp eax, -1
228bae: je 0x228ce3
228bb4: lea rdx, [rbp - 0x11]
228bb8: mov ecx, eax
228bba: call 0x276700
228bbf: test al, al
228bc1: jne 0x228b48
228bc3: mov rcx, qword ptr [rbp - 0x11]
228bc7: mov rax, qword ptr [rcx + 0x18]
228bcb: cmp qword ptr [rdi + 0x18], rax
228bcf: jne 0x228b48
228bd5: mov rbx, qword ptr [rcx + 0xc]
228bd9: cmp dword ptr [rdi + 0xf4], r12d
228be0: jne 0x228c12
228be2: movsx eax, word ptr [rdi + 0x15a]
228be9: movsx ecx, word ptr [rdi + 0x15c]
228bf0: imul eax, esi
228bf3: cdq 
228bf4: idiv dword ptr [rdi + 0x160]
228bfa: movsx r9d, ax
228bfe: sub r9d, ecx
228c01: mov word ptr [rdi + 0x15c], ax
228c08: add r9d, dword ptr [rdi + 0x14]
228c0c: mov dword ptr [rdi + 0x14], r9d
228c10: jmp 0x228c6f
228c12: mov rax, qword ptr [rcx]
228c15: call qword ptr [rax + 8]
228c18: cmp al, byte ptr [rip + 0x370b01] ; b'10AQaq`p'
228c1e: jne 0x228ccb
228c24: mov ecx, dword ptr [rdi + 0x6c]
228c27: lea rdx, [rbp - 0x11]
228c2b: call 0x276700
228c30: test al, al
228c32: jne 0x228ccb
228c38: mov rax, qword ptr [rbp - 0x11]
228c3c: lea r8, [rbp + 0xf]
228c40: lea rdx, [rbp + 0x17]
228c44: mov rcx, qword ptr [rax + 0x3c40]
228c4b: mov r9d, dword ptr [rax + 0x14]
228c4f: mov r10, qword ptr [rcx]
228c52: call qword ptr [r10 + 8]
228c56: mov r9d, dword ptr [rdi + 0x14]
228c5a: mov eax, r9d
228c5d: mov ecx, dword ptr [rbp + 0x23]
228c60: sub ecx, dword ptr [rbp + 0x1b]
228c63: sar ecx, 1
228c65: cmp r9d, ecx
228c68: cmovne eax, r9d
228c6c: mov dword ptr [rdi + 0x14], eax
228c6f: cmp dword ptr [rdi + 0x200], r12d
228c76: jne 0x228c81
228c78: cmp dword ptr [rdi + 0x210], r12d
228c7f: je 0x228ccb
228c81: lea r8, [rbp + 0xf]
228c85: mov qword ptr [rsp + 0x20], r12
228c8a: lea rdx, [rbp + 0x17]
228c8e: mov rcx, rdi
228c91: call 0x22b7b0
228c96: mov rcx, qword ptr [rip + 0x43e8c3] ; b''
228c9d: lea rdx, [rbp + 7]
228ca1: mov rcx, qword ptr [rcx + 0x210]
228ca8: call 0x41d9c0
228cad: mov edx, dword ptr [rbp + 0x23]
228cb0: mov eax, edx
228cb2: mov ecx, dword ptr [rbp + 0x1b]
228cb5: sub eax, ecx
228cb7: mov r8d, dword ptr [rbp + 0xb]
228cbb: cmp eax, r8d
228cbe: jl 0x228ccb
228cc0: sub ecx, edx
228cc2: lea eax, [r8 - 1]
228cc6: add eax, ecx
228cc8: add dword ptr [rdi + 0x14], eax
228ccb: mov rax, qword ptr [rdi]
228cce: mov rdx, rbx
228cd1: mov rcx, rdi
228cd4: call qword ptr [rax + 0x130]
228cda: mov qword ptr [rdi + 0xf8], rbx
228ce1: jmp 0x228d02
228ce3: mov eax, dword ptr [rdi + 0x14]
228ce6: cmp eax, ecx
228ce8: jle 0x228cef
228cea: sub eax, ecx
228cec: mov dword ptr [rdi + 0x14], eax
228cef: mov rax, qword ptr [rdi]
228cf2: mov rcx, rdi
228cf5: mov rdx, qword ptr [rdi + 0xf8]
228cfc: call qword ptr [rax + 0x130]
228d02: cmp dword ptr [rdi + 0x114], r12d
228d09: je 0x228d5c
228d0b: mov ecx, 0xe0
228d10: call 0x4f7a88
228d15: test rax, rax
228d18: je 0x228d3e
228d1a: movzx r9d, word ptr [rip + 0x3721be] ; b'\x19'
228d22: mov rcx, rax
228d25: movzx r8d, word ptr [rip + 0x3721d3] ; b'\x01'
228d2d: movzx edx, word ptr [rdi + 0xc8]
228d34: call 0x221000
228d39: mov rcx, rax
228d3c: jmp 0x228d41
228d3e: mov rcx, r12
228d41: movzx eax, byte ptr [rdi + 0x62]
228d45: lea r8, [rdi + 0xc]
228d49: mov r10, qword ptr [rcx]
228d4c: mov r9d, dword ptr [rdi + 0x14]
228d50: mov rdx, qword ptr [rdi + 0x18]
228d54: mov byte ptr [rsp + 0x20], al
228d58: call qword ptr [r10 + 0x10]
228d5c: mov r9d, dword ptr [rdi + 0x14]
228d60: lea rcx, [rdi + 0x120]
228d67: mov r8d, dword ptr [rdi + 0x10]
228d6b: mov edx, dword ptr [rdi + 0xc]
228d6e: call 0x40eae0
228d73: mov eax, dword ptr [rdi + 0x378]
228d79: lea r8d, [rax + 1]
228d7d: movzx eax, word ptr [rdi + 0x36c]
228d84: mov dword ptr [rdi + 0x378], r8d
228d8b: test ax, ax
228d8e: je 0x228da6
228d90: movzx ecx, ax
228d93: mov eax, r8d
228d96: cdq 
228d97: idiv ecx
228d99: test edx, edx
228d9b: jne 0x228da6
228d9d: lea rcx, [rdi + 0x354]
228da4: jmp 0x228de8
228da6: movzx eax, word ptr [rdi + 0x36e]
228dad: test ax, ax
228db0: je 0x228dc8
228db2: movzx ecx, ax
228db5: mov eax, r8d
228db8: cdq 
228db9: idiv ecx
228dbb: test edx, edx
228dbd: jne 0x228dc8
228dbf: lea rcx, [rdi + 0x35c]
228dc6: jmp 0x228de8
228dc8: movzx eax, word ptr [rdi + 0x370]
228dcf: test ax, ax
228dd2: je 0x228e1f
228dd4: movzx ecx, ax
228dd7: mov eax, r8d
228dda: cdq 
228ddb: idiv ecx
228ddd: test edx, edx
228ddf: jne 0x228e1f
228de1: lea rcx, [rdi + 0x364]
228de8: lea rdx, [rbp - 0x19]
228dec: call 0x3fff70
228df1: mov r9d, dword ptr [rdi + 0x48]
228df5: lea r8, [rbp - 9]
228df9: mov rdx, qword ptr [rdi + 0x18]
228dfd: mov rcx, rax
228e00: mov eax, dword ptr [rdi + 0x14]
228e03: mov dword ptr [rsp + 0x38], r12d
228e08: mov dword ptr [rsp + 0x30], r13d
228e0d: mov dword ptr [rsp + 0x28], eax
228e11: lea rax, [rbp - 9]
228e15: mov qword ptr [rsp + 0x20], rax
228e1a: call 0x258da0
228e1f: mov rsi, qword ptr [rsp + 0x100]
228e27: mov r12, qword ptr [rsp + 0x108]
228e2f: mov r13, qword ptr [rsp + 0xd0]
228e37: mov rbx, qword ptr [rsp + 0xf8]
228e3f: mov r14, qword ptr [rsp + 0xc8]
228e47: mov rcx, qword ptr [rbp + 0x27]
228e4b: xor rcx, rsp
228e4e: call 0x4f77a0
228e53: add rsp, 0xd8
228e5a: pop rdi
228e5b: pop rbp
228e5c: ret 
