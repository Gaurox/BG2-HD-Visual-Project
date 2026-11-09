22bf00: mov qword ptr [rsp + 0x18], rbx
22bf05: push rbp
22bf06: push rsi
22bf07: push rdi
22bf08: push r12
22bf0a: push r13
22bf0c: push r14
22bf0e: push r15
22bf10: lea rbp, [rsp - 0x60]
22bf15: sub rsp, 0x160
22bf1c: mov rax, qword ptr [rip + 0x438ab5] ; b'2\xa2\xdf-\x99+'
22bf23: xor rax, rsp
22bf26: mov qword ptr [rbp + 0x58], rax
22bf2a: mov rax, qword ptr [rip + 0x430bdf] ; b'$\xcbe@\x01'
22bf31: mov rsi, rdx
22bf34: mov qword ptr [rsp + 0x68], rdx
22bf39: movzx r13d, cx
22bf3d: mov word ptr [rbp - 0x80], cx
22bf41: lea rdx, [rip + 0x42f3a0] ; b''
22bf48: xor edi, edi
22bf4a: mov qword ptr [rsp + 0x60], rax
22bf4f: lea rcx, [rbp + 0x28]
22bf53: mov dword ptr [rbp - 0x7c], edi
22bf56: mov qword ptr [rsp + 0x58], rax
22bf5b: xor ebx, ebx
22bf5d: mov qword ptr [rsp + 0x50], rax
22bf62: mov qword ptr [rbp + 0x28], rax
22bf66: call 0x11ea00
22bf6b: movzx r15d, r13w
22bf6f: mov dword ptr [rbp - 0x7c], r15d
22bf73: cmp r13w, 0xe
22bf78: jne 0x22bf84
22bf7a: mov r15d, 4
22bf80: mov dword ptr [rbp - 0x7c], r15d
22bf84: movzx r12d, r15w
22bf88: lea rdx, [rip - 0x22bf8f]
22bf8f: dec r12d
22bf92: mov r14d, 1
22bf98: cmp r12d, 0xfe
22bf9f: ja 0x22e8f5
22bfa5: movsxd rax, r12d
22bfa8: movzx eax, byte ptr [rdx + rax + 0x22eebc]
22bfb0: mov ecx, dword ptr [rdx + rax*4 + 0x22eddc]
22bfb7: add rcx, rdx
22bfba: jmp rcx
22bfbc: mov ecx, 0x1b8
22bfc1: call 0x4f7a88
22bfc6: mov rbx, rax
22bfc9: test rax, rax
22bfcc: je 0x22bff5
22bfce: xor edx, edx
22bfd0: mov r8d, 0x1b8
22bfd6: mov rcx, rax
22bfd9: call 0x4fab70
22bfde: mov rcx, rbx
22bfe1: call 0x226910
22bfe6: lea rax, [rip + 0x370003] ; b'\xf0\x80"@\x01'
22bfed: mov qword ptr [rbx], rax
22bff0: jmp 0x22e8ec
22bff5: xor ebx, ebx
22bff7: jmp 0x22e8f5
22bffc: mov ecx, 0x3c0
22c001: call 0x4f7a88
22c006: mov rbx, rax
22c009: test rax, rax
22c00c: je 0x22c12d
22c012: lea rdx, [rip + 0x370a4f] ; b'SPBRNHND'
22c019: lea rcx, [rbp - 0x20]
22c01d: call 0x3ff800
22c022: mov rcx, rbx
22c025: mov rdx, qword ptr [rax]
22c028: call 0x227600
22c02d: mov rcx, qword ptr [rbx + 0x1b8]
22c034: lea rax, [rip + 0x36f85d] ; b'`\x82"@\x01'
22c03b: xor edx, edx
22c03d: mov qword ptr [rbx], rax
22c040: call 0x412380
22c045: mov rax, qword ptr [rip + 0x43b4fc] ; b''
22c04c: lea rcx, [rbx + 0x1c8]
22c053: xor edx, edx
22c055: mov r9, qword ptr [rax + 0x1090]
22c05c: add r9, 0x63d8
22c063: lea r8d, [rdx + 0x43]
22c067: call 0x4221c0
22c06c: mov rcx, qword ptr [rbx + 0x1b8]
22c073: lea rdx, [rbx + 0x1c8]
22c07a: call 0x412390
22c07f: xor ecx, ecx
22c081: mov dword ptr [rsp + 0x78], 0x14
22c089: mov qword ptr [rbx + 0x1f8], rcx
22c090: lea r8, [rip + 0x3bf716] ; b''
22c097: mov dword ptr [rbx + 0x200], ecx
22c09d: lea rdx, [rbp - 0x18]
22c0a1: mov dword ptr [rbx + 0x210], ecx
22c0a7: lea rcx, [rbx + 0x140]
22c0ae: mov dword ptr [rsp + 0x7c], 0xf
22c0b6: mov rax, qword ptr [rsp + 0x78]
22c0bb: mov qword ptr [rbx + 0x204], rax
22c0c2: mov eax, 0x80
22c0c7: mov word ptr [rbx + 0x20c], ax
22c0ce: mov eax, 5
22c0d3: mov word ptr [rbx + 0x214], ax
22c0da: call 0x3ff960
22c0df: mov eax, 0x1e
22c0e4: mov dword ptr [rbx + 0x70], 0xffffffff
22c0eb: lea rcx, [rbx + 0x178]
22c0f2: mov word ptr [rbx + 0x3b8], ax
22c0f9: lea rdx, [rip + 0x3bf6ad] ; b''
22c100: call 0x3fd810
22c105: mov dword ptr [rsp + 0x78], 0x17
22c10d: mov dword ptr [rsp + 0x7c], 0x32
22c115: mov rax, qword ptr [rsp + 0x78]
22c11a: mov qword ptr [rbx + 0x164], rax
22c121: mov dword ptr [rbx + 0x180], 0xffffffff
22c12b: jmp 0x22c12f
22c12d: xor ebx, ebx
22c12f: lea rcx, [rbx + 0x140]
22c136: mov byte ptr [rbx + 0x158], r14b
22c13d: lea r8, [rip + 0x37070c] ; b'TRA_30'
22c144: lea rdx, [rbp - 0x20]
22c148: call 0x3ff960
22c14d: lea rdx, [rbp - 0x20]
22c151: jmp 0x22e8d9
22c156: mov ecx, 0x3c0
22c15b: call 0x4f7a88
22c160: test rax, rax
22c163: je 0x22c170
22c165: mov rcx, rax
22c168: call 0x227800
22c16d: mov rbx, rax
22c170: lea rcx, [rbx + 0x140]
22c177: mov byte ptr [rbx + 0x158], r14b
22c17e: lea r8, [rip + 0x3706d3] ; b'TRA_08'
22c185: lea rdx, [rbp - 0x20]
22c189: call 0x3ff960
22c18e: lea rdx, [rbp - 0x20]
22c192: jmp 0x22e8d9
22c197: mov ecx, 0x3c0
22c19c: call 0x4f7a88
22c1a1: test rax, rax
22c1a4: je 0x22c1b1
22c1a6: mov rcx, rax
22c1a9: call 0x227800
22c1ae: mov rbx, rax
22c1b1: xor edx, edx
22c1b3: mov byte ptr [rbx + 0x158], r14b
22c1ba: mov rcx, rbx
22c1bd: lea r8d, [rdx + 0x43]
22c1c1: call 0x235d80
22c1c6: lea rcx, [rbx + 0x140]
22c1cd: lea r8, [rip + 0x37068c] ; b'EFF_M20'
22c1d4: lea rdx, [rbp - 0x20]
22c1d8: call 0x3ff960
22c1dd: lea rdx, [rbp - 0x20]
22c1e1: jmp 0x22e8d9
22c1e6: lea rdx, [rip + 0x37067b] ; b'Spsmkjet'
22c1ed: lea rcx, [rsp + 0x60]
22c1f2: call 0x3fd810
22c1f7: lea rdx, [rip + 0x3bf5af] ; b''
22c1fe: lea rcx, [rsp + 0x50]
22c203: call 0x3fd810
22c208: lea rdx, [rip + 0x3bf59e] ; b''
22c20f: lea rcx, [rsp + 0x58]
22c214: call 0x3fd810
22c219: mov ecx, 0x418
22c21e: call 0x4f7a88
22c223: mov rbx, rax
22c226: test rax, rax
22c229: je 0x22c30e
22c22f: mov rcx, rax
22c232: call 0x226910
22c237: lea rax, [rip + 0x370142] ; b'0\x81"@\x01'
22c23e: lea rcx, [rbx + 0x1b8]
22c245: mov qword ptr [rbx], rax
22c248: call 0x410f70
22c24d: lea rcx, [rbx + 0x2f0]
22c254: call 0x410d80
22c259: lea rdx, [rsp + 0x60]
22c25e: lea rcx, [rbp - 0x20]
22c262: call 0x3ff710
22c267: lea rcx, [rbx + 0x2c0]
22c26e: mov r9d, r14d
22c271: mov r8d, r14d
22c274: lea rdx, [rbp - 0x20]
22c278: call 0x14d080
22c27d: mov rax, qword ptr [rsp + 0x50]
22c282: cmp dword ptr [rax - 8], edi
22c285: je 0x22c2b1
22c287: lea rdx, [rsp + 0x50]
22c28c: lea rcx, [rbp - 0x18]
22c290: call 0x3ff710
22c295: mov r9d, r14d
22c298: lea rdx, [rbp - 0x18]
22c29c: mov r8d, r14d
22c29f: lea rcx, [rbx + 0x2f0]
22c2a6: call 0x18aa40
22c2ab: movzx eax, r14b
22c2af: jmp 0x22c2b3
22c2b1: xor al, al
22c2b3: xor edx, edx
22c2b5: mov byte ptr [rbx + 0x414], al
22c2bb: lea rcx, [rbx + 0x1b8]
22c2c2: call 0x412380
22c2c7: xor edx, edx
22c2c9: lea rcx, [rbx + 0x1b8]
22c2d0: call 0x411610
22c2d5: lea rcx, [rbx + 0x140]
22c2dc: lea r8, [rsp + 0x58]
22c2e1: lea rdx, [rbp - 0x10]
22c2e5: call 0x3ff890
22c2ea: lea rax, [rip + 0x3701bf] ; b'0\x81"@\x01'
22c2f1: mov dword ptr [rbx + 0x410], 8
22c2fb: mov qword ptr [rbx], rax
22c2fe: mov byte ptr [rbx + 0x415], dil
22c305: mov byte ptr [rbx + 0x158], r14b
22c30c: jmp 0x22c310
22c30e: xor ebx, ebx
22c310: lea r8, [rip + 0x3bf496] ; b''
22c317: lea rdx, [rbp - 0x20]
22c31b: lea rcx, [rbx + 0x140]
22c322: call 0x3ff960
22c327: lea rdx, [rbp - 0x20]
22c32b: jmp 0x22e8d9
22c330: mov ecx, 0x328
22c335: call 0x4f7a88
22c33a: mov rbx, rax
22c33d: test rax, rax
22c340: je 0x22c392
22c342: lea rdx, [rip + 0x3bf464] ; b''
22c349: lea rcx, [rbp - 0x68]
22c34d: call 0x3fd6b0
22c352: lea rdx, [rip + 0x36cedf] ; b'FlmStrk'
22c359: lea rcx, [rbp - 0x70]
22c35d: call 0x3fd6b0
22c362: movzx ecx, byte ptr [rip + 0x3723eb] ; b'\x0f<\x05\x18\xe0\xa5\x01'
22c369: lea r8, [rbp - 0x68]
22c36d: add cx, cx
22c370: lea rdx, [rbp - 0x70]
22c374: mov word ptr [rsp + 0x28], cx
22c379: mov r9b, 0xff
22c37c: mov rcx, rbx
22c37f: mov dword ptr [rsp + 0x20], edi
22c383: call 0x227cd0
22c388: mov rbx, rax
22c38b: mov edi, 3
22c390: jmp 0x22c394
22c392: xor ebx, ebx
22c394: test dil, 2
22c398: je 0x22c3a6
22c39a: and edi, 0xfffffffd
22c39d: lea rcx, [rbp - 0x70]
22c3a1: call 0x3fd740
22c3a6: test r14b, dil
22c3a9: je 0x22c310
22c3af: lea rcx, [rbp - 0x68]
22c3b3: call 0x3fd740
22c3b8: jmp 0x22c310
22c3bd: mov ecx, 0x328
22c3c2: call 0x4f7a88
22c3c7: mov rbx, rax
22c3ca: test rax, rax
22c3cd: je 0x22c422
22c3cf: lea rdx, [rip + 0x3bf3d7] ; b''
22c3d6: lea rcx, [rsp + 0x70]
22c3db: call 0x3fd6b0
22c3e0: lea rdx, [rip + 0x36ce59] ; b'HLYMITE'
22c3e7: lea rcx, [rbp - 0x60]
22c3eb: call 0x3fd6b0
22c3f0: movzx ecx, byte ptr [rip + 0x37235d] ; b'\x0f<\x05\x18\xe0\xa5\x01'
22c3f7: lea r8, [rsp + 0x70]
22c3fc: add cx, cx
22c3ff: lea rdx, [rbp - 0x60]
22c403: mov word ptr [rsp + 0x28], cx
22c408: mov r9b, 0xff
22c40b: mov rcx, rbx
22c40e: mov dword ptr [rsp + 0x20], r14d
22c413: call 0x227cd0
22c418: mov rbx, rax
22c41b: mov edi, 0xc
22c420: jmp 0x22c424
22c422: xor ebx, ebx
22c424: test dil, 8
22c428: je 0x22c436
22c42a: and edi, 0xfffffff7
22c42d: lea rcx, [rbp - 0x60]
22c431: call 0x3fd740
22c436: test dil, 4
22c43a: je 0x22c310
22c440: lea rcx, [rsp + 0x70]
22c445: call 0x3fd740
22c44a: jmp 0x22c310
22c44f: mov ecx, 0x3f0
22c454: call 0x4f7a88
22c459: mov rbx, rax
22c45c: test rax, rax
22c45f: je 0x22c618
22c465: movzx edi, word ptr [rip + 0x394210] ; b'\x01'
22c46c: lea rdx, [rip + 0x3705c5] ; b'SPMAGMIS'
22c473: lea rcx, [rbp - 0x18]
22c477: call 0x3ff800
22c47c: mov rcx, rbx
22c47f: mov rdx, qword ptr [rax]
22c482: call 0x227600
22c487: lea rax, [rip + 0x36fa2a] ; b'0\x83"@\x01'
22c48e: mov edx, 0xa
22c493: lea rcx, [rbx + 0x3b8]
22c49a: mov qword ptr [rbx], rax
22c49d: call 0x4073a0
22c4a2: lea rax, [rip + 0x3608af] ; b'\x90n\x11@\x01'
22c4a9: xor edx, edx
22c4ab: mov qword ptr [rbx + 0x3b8], rax
22c4b2: mov rcx, qword ptr [rbx + 0x1b8]
22c4b9: call 0x412380
22c4be: or dword ptr [rbx + 0x118], 8
22c4c5: cmp di, r14w
22c4c9: jne 0x22c505
22c4cb: mov rax, qword ptr [rip + 0x43b076] ; b''
22c4d2: lea rcx, [rbx + 0x1c8]
22c4d9: xor edx, edx
22c4db: mov r9, qword ptr [rax + 0x1090]
22c4e2: add r9, 0x63d8
22c4e9: lea r8d, [rdx + 0x21]
22c4ed: call 0x4221c0
22c4f2: mov rcx, qword ptr [rbx + 0x1b8]
22c4f9: lea rdx, [rbx + 0x1c8]
22c500: call 0x412390
22c505: lea eax, [r15 - 0x43]
22c509: xor edi, edi
22c50b: movsx r15d, ax
22c50f: test r15d, r15d
22c512: jle 0x22c566
22c514: mov ecx, 0x25
22c519: xor edx, edx
22c51b: call 0x22bf00
22c520: mov rsi, rax
22c523: test edi, edi
22c525: je 0x22c54b
22c527: lea rdx, [rip + 0x3bf27f] ; b''
22c52e: lea rcx, [rbp - 0x20]
22c532: call 0x3ff7c0
22c537: lea rcx, [rsi + 0x140]
22c53e: lea r8, [rbp - 0x20]
22c542: lea rdx, [rbp - 0x10]
22c546: call 0x3ff880
22c54b: mov rdx, rsi
22c54e: lea rcx, [rbx + 0x3b8]
22c555: call 0x4075c0
22c55a: inc edi
22c55c: cmp edi, r15d
22c55f: jl 0x22c514
22c561: mov rsi, qword ptr [rsp + 0x68]
22c566: lea rdx, [rip + 0x3bf240] ; b''
22c56d: mov dword ptr [rbx + 0x70], 0xffffffff
22c574: lea rcx, [rbx + 0x178]
22c57b: call 0x3fd810
22c580: xor edx, edx
22c582: mov dword ptr [rsp + 0x70], 0xa
22c58a: mov ecx, r14d
22c58d: mov qword ptr [rbx + 0x1f8], rdx
22c594: lea rax, [rip + 0x36f91d] ; b'0\x83"@\x01'
22c59b: mov dword ptr [rbx + 0x200], ecx
22c5a1: mov qword ptr [rbx], rax
22c5a4: lea r8, [rip + 0x3bf202] ; b''
22c5ab: mov dword ptr [rbx + 0x210], edx
22c5b1: lea rdx, [rbp + 8]
22c5b5: mov word ptr [rbx + 0x214], cx
22c5bc: lea rcx, [rbx + 0x140]
22c5c3: mov dword ptr [rsp + 0x74], 7
22c5cb: mov rax, qword ptr [rsp + 0x70]
22c5d0: mov qword ptr [rbx + 0x204], rax
22c5d7: mov eax, 0x80
22c5dc: mov word ptr [rbx + 0x20c], ax
22c5e3: mov dword ptr [rbx + 0x180], 0xffffffff
22c5ed: call 0x3ff960
22c5f2: lea rdx, [rip + 0x3bf1b4] ; b''
22c5f9: mov dword ptr [rbx + 0x70], 0xffffffff
22c600: lea rcx, [rbx + 0x178]
22c607: call 0x3fd810
22c60c: mov dword ptr [rbx + 0x180], 0xffffffff
22c616: jmp 0x22c61a
22c618: xor ebx, ebx
22c61a: lea rcx, [rbx + 0x140]
22c621: lea r8, [rip + 0x37024c] ; b'TRA_22'
22c628: lea rdx, [rbp - 0x20]
22c62c: call 0x3ff960
22c631: lea rcx, [rbx + 0x14c]
22c638: lea r8, [rip + 0x3bf16e] ; b''
22c63f: lea rdx, [rbp - 0x20]
22c643: call 0x3ff960
22c648: mov byte ptr [rbx + 0x158], r14b
22c64f: jmp 0x22e8ec
22c654: mov ecx, 0x3b8
22c659: call 0x4f7a88
22c65e: test rax, rax
22c661: je 0x22e8f5
22c667: mov rcx, rax
22c66a: call 0x227a40
22c66f: mov rbx, rax
22c672: jmp 0x22e8ec
22c677: mov ecx, 0x400
22c67c: call 0x4f7a88
22c681: mov rbx, rax
22c684: test rax, rax
22c687: je 0x22c87d
22c68d: mov rax, qword ptr [rip + 0x43047c] ; b'$\xcbe@\x01'
22c694: lea rdx, [rip + 0x42ec4d] ; b''
22c69b: lea rcx, [rbp + 0x10]
22c69f: mov qword ptr [rbp + 0x10], rax
22c6a3: call 0x11ea00
22c6a8: lea rdx, [rip + 0x370389] ; b'SPMAGMIS'
22c6af: lea rcx, [rbp - 0x20]
22c6b3: call 0x3ff800
22c6b8: mov rcx, rbx
22c6bb: mov rdx, qword ptr [rax]
22c6be: call 0x227600
22c6c3: mov dword ptr [rsp + 0x40], 0xffffffff
22c6cb: lea rax, [rip + 0x36ff0e] ; b'\x10\x82"@\x01'
22c6d2: mov byte ptr [rsp + 0x38], dil
22c6d7: lea rcx, [rbx + 0x3d8]
22c6de: mov byte ptr [rsp + 0x30], dil
22c6e3: xor r9d, r9d
22c6e6: mov byte ptr [rsp + 0x28], dil
22c6eb: xor r8d, r8d
22c6ee: xor edx, edx
22c6f0: mov byte ptr [rsp + 0x20], dil
22c6f5: mov qword ptr [rbx], rax
22c6f8: call 0x11ba20
22c6fd: mov rcx, qword ptr [rbx + 0x1b8]
22c704: xor edx, edx
22c706: mov dword ptr [rbx + 0x11c], edi
22c70c: call 0x412380
22c711: lea eax, [r15 - 0x50]
22c715: mov dword ptr [rbx + 0x3bc], r14d
22c71c: mov word ptr [rbx + 0x3b8], ax
22c723: lea rdx, [rbp + 0x10]
22c727: mov eax, 0x16
22c72c: lea rcx, [rbx + 0x3d8]
22c733: mov word ptr [rbx + 0x3c0], ax
22c73a: xor r15d, r15d
22c73d: mov eax, 0x5a
22c742: mov dword ptr [rbx + 0x3d0], r15d
22c749: mov word ptr [rbx + 0x3ba], ax
22c750: call 0x11ea00
22c755: movzx ecx, word ptr [rbx + 0x3c0]
22c75c: xor edx, edx
22c75e: inc cx
22c761: call 0x22bf00
22c766: lea rdx, [rip + 0x3bf040] ; b''
22c76d: mov qword ptr [rbx + 0x3c8], rax
22c774: lea rcx, [rbx + 0x178]
22c77b: mov dword ptr [rbx + 0x70], 0xffffffff
22c782: call 0x3fd810
22c787: lea rcx, [rbp + 0x10]
22c78b: mov dword ptr [rbx + 0x180], 0xffffffff
22c795: call 0x3fd740
22c79a: lea rax, [rip + 0x36fe3f] ; b'\x10\x82"@\x01'
22c7a1: mov dword ptr [rsp + 0x70], 0xa
22c7a9: mov qword ptr [rbx], rax
22c7ac: lea rcx, [rbx + 0x140]
22c7b3: mov dword ptr [rsp + 0x74], 7
22c7bb: lea r8, [rip + 0x3befeb] ; b''
22c7c2: mov rax, qword ptr [rsp + 0x70]
22c7c7: lea rdx, [rbp - 0x18]
22c7cb: mov qword ptr [rbx + 0x204], rax
22c7d2: mov eax, 0x80
22c7d7: mov word ptr [rbx + 0x20c], ax
22c7de: mov qword ptr [rbx + 0x1f8], r15
22c7e5: mov dword ptr [rbx + 0x200], r14d
22c7ec: mov dword ptr [rbx + 0x210], r15d
22c7f3: mov word ptr [rbx + 0x214], r14w
22c7fb: call 0x3ff960
22c800: lea rdx, [rip + 0x3befa6] ; b''
22c807: mov dword ptr [rbx + 0x70], 0xffffffff
22c80e: lea rcx, [rbx + 0x178]
22c815: call 0x3fd810
22c81a: mov dword ptr [rsp + 0x40], 0xffffffff
22c822: lea rcx, [rbp + 0x40]
22c826: mov byte ptr [rsp + 0x38], dil
22c82b: xor r9d, r9d
22c82e: mov byte ptr [rsp + 0x30], dil
22c833: xor r8d, r8d
22c836: mov byte ptr [rsp + 0x28], dil
22c83b: xor edx, edx
22c83d: mov byte ptr [rsp + 0x20], dil
22c842: mov dword ptr [rbx + 0x180], 0xffffffff
22c84c: call 0x11ba20
22c851: movzx eax, byte ptr [rip + 0x360694] ; b'\x1f\xc7~\xfd\xc6\x1d\x1c\xc9\xca\x0f\x01\x02\x03\x04\x05\xff\x06\x01\x02\x03\x04\x05\x06\x07efghijklmno'
22c858: lea rdx, [rbp + 0x40]
22c85c: lea rcx, [rbx + 0x3d8]
22c863: mov byte ptr [rbp + 0x48], al
22c866: call 0x11ea00
22c86b: lea rcx, [rbp + 0x40]
22c86f: mov dword ptr [rbx + 0x3f8], r14d
22c876: call 0x3fd740
22c87b: jmp 0x22c87f
22c87d: xor ebx, ebx
22c87f: mov rax, qword ptr [rsi]
22c882: mov rcx, rsi
22c885: call qword ptr [rax + 0x20]
22c888: movzx ecx, byte ptr [rip + 0x36065e] ; b'\xc7~\xfd\xc6\x1d\x1c\xc9\xca\x0f\x01\x02\x03\x04\x05\xff\x06\x01\x02\x03\x04\x05\x06\x07efghijklmnop'
22c88f: lea rdx, [rbp + 0x28]
22c893: cmp byte ptr [rax + 8], cl
22c896: ja 0x22c8b3
22c898: movzx eax, byte ptr [rip + 0x36064b] ; b'\xc8\x80\x1f\xc7~\xfd\xc6\x1d\x1c\xc9\xca\x0f\x01\x02\x03\x04\x05\xff\x06\x01\x02\x03\x04\x05\x06\x07efghijklm'
22c89f: mov rcx, rbx
22c8a2: mov byte ptr [rbp + 0x30], al
22c8a5: mov rax, qword ptr [rbx]
22c8a8: call qword ptr [rax + 0x120]
22c8ae: jmp 0x22e8ec
22c8b3: mov byte ptr [rbp + 0x30], cl
22c8b6: mov rcx, rbx
22c8b9: mov rax, qword ptr [rbx]
22c8bc: call qword ptr [rax + 0x120]
22c8c2: jmp 0x22e8ec
22c8c7: mov ecx, 0x3c0
22c8cc: call 0x4f7a88
22c8d1: mov rbx, rax
22c8d4: test rax, rax
22c8d7: je 0x22c9cf
22c8dd: lea rdx, [rip + 0x370174] ; b'COLRSPRY'
22c8e4: lea rcx, [rbp - 0x20]
22c8e8: call 0x3ff800
22c8ed: mov rcx, rbx
22c8f0: mov rdx, qword ptr [rax]
22c8f3: call 0x227600
22c8f8: mov rcx, qword ptr [rbx + 0x1b8]
22c8ff: lea rax, [rip + 0x36ee5a] ; b'`\x82"@\x01'
22c906: xor edx, edx
22c908: mov qword ptr [rbx], rax
22c90b: call 0x412380
22c910: xor ecx, ecx
22c912: mov dword ptr [rsp + 0x70], 0x14
22c91a: mov qword ptr [rbx + 0x1f8], rcx
22c921: lea r8, [rip + 0x3bee85] ; b''
22c928: mov dword ptr [rbx + 0x200], ecx
22c92e: lea rdx, [rbp - 0x18]
22c932: mov dword ptr [rbx + 0x210], ecx
22c938: lea rcx, [rbx + 0x140]
22c93f: mov dword ptr [rsp + 0x74], 0xf
22c947: mov rax, qword ptr [rsp + 0x70]
22c94c: mov qword ptr [rbx + 0x204], rax
22c953: mov eax, 0x80
22c958: mov word ptr [rbx + 0x20c], ax
22c95f: mov eax, 5
22c964: mov word ptr [rbx + 0x214], ax
22c96b: call 0x3ff960
22c970: mov eax, 0x37
22c975: mov dword ptr [rbx + 0x70], 0xffffffff
22c97c: lea rcx, [rbx + 0x178]
22c983: mov word ptr [rbx + 0x3b8], ax
22c98a: lea rdx, [rip + 0x3bee1c] ; b''
22c991: call 0x3fd810
22c996: mov dword ptr [rsp + 0x70], 0x2d
22c99e: lea r8, [rip + 0x36fed7] ; b'TRA_05'
22c9a5: mov dword ptr [rsp + 0x74], 0x46
22c9ad: mov rax, qword ptr [rsp + 0x70]
22c9b2: mov qword ptr [rbx + 0x164], rax
22c9b9: mov dword ptr [rbx + 0x180], 0xffffffff
22c9c3: mov byte ptr [rbx + 0x158], r14b
22c9ca: jmp 0x22c317
22c9cf: xor ebx, ebx
22c9d1: lea r8, [rip + 0x36fea4] ; b'TRA_05'
22c9d8: mov byte ptr [rbx + 0x158], r14b
22c9df: jmp 0x22c317
22c9e4: mov ecx, 0x428
22c9e9: call 0x4f7a88
22c9ee: mov rbx, rax
22c9f1: test rax, rax
22c9f4: je 0x22cb35
22c9fa: lea rdx, [rip + 0x3bedac] ; b''
22ca01: lea rcx, [rsp + 0x78]
22ca06: call 0x3fd6b0
22ca0b: lea rdx, [rip + 0x3bed9b] ; b''
22ca12: lea rcx, [rbp - 0x58]
22ca16: call 0x3fd6b0
22ca1b: lea rdx, [rip + 0x36fe66] ; b'SPDimDr'
22ca22: lea rcx, [rbp - 0x78]
22ca26: call 0x3fd6b0
22ca2b: mov rcx, rbx
22ca2e: call 0x226910
22ca33: lea rax, [rip + 0x36f6e6] ; b'P\x84"@\x01'
22ca3a: lea rcx, [rbx + 0x1b8]
22ca41: mov qword ptr [rbx], rax
22ca44: call 0x410f70
22ca49: lea rcx, [rbx + 0x2f0]
22ca50: call 0x410d80
22ca55: mov rax, qword ptr [rip + 0x4300b4] ; b'$\xcbe@\x01'
22ca5c: lea rcx, [rbx + 0x418]
22ca63: lea rdx, [rbp - 0x78]
22ca67: mov qword ptr [rcx], rax
22ca6a: call 0x3fd770
22ca6f: lea r8, [rip + 0x3de1c6] ; b'2'
22ca76: lea rdx, [rbp - 0x78]
22ca7a: lea rcx, [rbp - 0x18]
22ca7e: call 0x3fd8e0
22ca83: mov rdx, rax
22ca86: lea rcx, [rbp - 0x20]
22ca8a: call 0x3ff710
22ca8f: lea rcx, [rbx + 0x2c0]
22ca96: mov r9d, r14d
22ca99: mov r8d, r14d
22ca9c: lea rdx, [rbp - 0x20]
22caa0: call 0x14d080
22caa5: lea rcx, [rbp - 0x18]
22caa9: call 0x3fd740
22caae: mov rax, qword ptr [rsp + 0x78]
22cab3: cmp dword ptr [rax - 8], edi
22cab6: je 0x22cae2
22cab8: lea rdx, [rsp + 0x78]
22cabd: lea rcx, [rbp - 0x10]
22cac1: call 0x3ff710
22cac6: mov r9d, r14d
22cac9: lea rdx, [rbp - 0x10]
22cacd: mov r8d, r14d
22cad0: lea rcx, [rbx + 0x2f0]
22cad7: call 0x18aa40
22cadc: movzx eax, r14b
22cae0: jmp 0x22cae4
22cae2: xor al, al
22cae4: xor edx, edx
22cae6: mov byte ptr [rbx + 0x414], al
22caec: lea rcx, [rbx + 0x1b8]
22caf3: call 0x412380
22caf8: xor edx, edx
22cafa: lea rcx, [rbx + 0x1b8]
22cb01: call 0x411610
22cb06: lea rcx, [rbx + 0x140]
22cb0d: lea r8, [rbp - 0x58]
22cb11: lea rdx, [rbp + 8]
22cb15: call 0x3ff890
22cb1a: mov dword ptr [rbx + 0x410], edi
22cb20: mov byte ptr [rbx + 0x415], dil
22cb27: mov byte ptr [rbx + 0x420], dil
22cb2e: mov edi, 0x70
22cb33: jmp 0x22cb37
22cb35: xor ebx, ebx
22cb37: test dil, 0x40
22cb3b: je 0x22cb49
22cb3d: and edi, 0xffffffbf
22cb40: lea rcx, [rbp - 0x78]
22cb44: call 0x3fd740
22cb49: test dil, 0x20
22cb4d: je 0x22cb5b
22cb4f: and edi, 0xffffffdf
22cb52: lea rcx, [rbp - 0x58]
22cb56: call 0x3fd740
22cb5b: test dil, 0x10
22cb5f: je 0x22cb6b
22cb61: lea rcx, [rsp + 0x78]
22cb66: call 0x3fd740
22cb6b: lea r8, [rip + 0x36fd1e] ; b'EFF_M09'
22cb72: jmp 0x22c317
22cb77: lea rdx, [rip + 0x36c6ca] ; b'SHAir'
22cb7e: lea rcx, [rsp + 0x60]
22cb83: call 0x3fd810
22cb88: lea rdx, [rip + 0x3bec1e] ; b''
22cb8f: lea rcx, [rsp + 0x50]
22cb94: call 0x3fd810
22cb99: lea rdx, [rip + 0x3bec0d] ; b''
22cba0: lea rcx, [rsp + 0x58]
22cba5: call 0x3fd810
22cbaa: mov ecx, 0x418
22cbaf: call 0x4f7a88
22cbb4: mov rbx, rax
22cbb7: test rax, rax
22cbba: je 0x22c30e
22cbc0: mov rcx, rax
22cbc3: call 0x226910
22cbc8: lea rax, [rip + 0x36f7b1] ; b'0\x81"@\x01'
22cbcf: lea rcx, [rbx + 0x1b8]
22cbd6: mov qword ptr [rbx], rax
22cbd9: call 0x410f70
22cbde: lea rcx, [rbx + 0x2f0]
22cbe5: call 0x410d80
22cbea: lea rdx, [rsp + 0x60]
22cbef: lea rcx, [rbp - 0x20]
22cbf3: call 0x3ff710
22cbf8: lea rcx, [rbx + 0x2c0]
22cbff: mov r9d, r14d
22cc02: mov r8d, r14d
22cc05: lea rdx, [rbp - 0x20]
22cc09: call 0x14d080
22cc0e: mov rax, qword ptr [rsp + 0x50]
22cc13: cmp dword ptr [rax - 8], edi
22cc16: je 0x22cc42
22cc18: lea rdx, [rsp + 0x50]
22cc1d: lea rcx, [rbp - 0x18]
22cc21: call 0x3ff710
22cc26: mov r9d, r14d
22cc29: lea rdx, [rbp - 0x18]
22cc2d: mov r8d, r14d
22cc30: lea rcx, [rbx + 0x2f0]
22cc37: call 0x18aa40
22cc3c: movzx eax, r14b
22cc40: jmp 0x22cc44
22cc42: xor al, al
22cc44: xor edx, edx
22cc46: mov byte ptr [rbx + 0x414], al
22cc4c: lea rcx, [rbx + 0x1b8]
22cc53: call 0x412380
22cc58: xor edx, edx
22cc5a: lea rcx, [rbx + 0x1b8]
22cc61: call 0x411610
22cc66: lea rcx, [rbx + 0x140]
22cc6d: lea r8, [rsp + 0x58]
22cc72: lea rdx, [rbp - 0x10]
22cc76: call 0x3ff890
22cc7b: mov dword ptr [rbx + 0x410], 8
22cc85: mov byte ptr [rbx + 0x415], dil
22cc8c: mov byte ptr [rbx + 0x158], r14b
22cc93: jmp 0x22c310
22cc98: lea rdx, [rip + 0x36c5d9] ; b'SHEarth'
22cc9f: lea rcx, [rsp + 0x60]
22cca4: call 0x3fd810
22cca9: lea rdx, [rip + 0x3beafd] ; b''
22ccb0: lea rcx, [rsp + 0x50]
22ccb5: call 0x3fd810
22ccba: lea rdx, [rip + 0x3beaec] ; b''
22ccc1: lea rcx, [rsp + 0x58]
22ccc6: call 0x3fd810
22cccb: mov ecx, 0x418
22ccd0: call 0x4f7a88
22ccd5: mov rbx, rax
22ccd8: test rax, rax
22ccdb: je 0x22c30e
22cce1: mov rcx, rax
22cce4: call 0x226910
22cce9: lea rax, [rip + 0x36f690] ; b'0\x81"@\x01'
22ccf0: lea rcx, [rbx + 0x1b8]
22ccf7: mov qword ptr [rbx], rax
22ccfa: call 0x410f70
22ccff: lea rcx, [rbx + 0x2f0]
22cd06: call 0x410d80
22cd0b: lea rdx, [rsp + 0x60]
22cd10: lea rcx, [rbp - 0x20]
22cd14: call 0x3ff710
22cd19: lea rcx, [rbx + 0x2c0]
22cd20: mov r9d, r14d
22cd23: mov r8d, r14d
22cd26: lea rdx, [rbp - 0x20]
22cd2a: call 0x14d080
22cd2f: mov rax, qword ptr [rsp + 0x50]
22cd34: cmp dword ptr [rax - 8], edi
22cd37: je 0x22cc42
22cd3d: lea rdx, [rsp + 0x50]
22cd42: lea rcx, [rbp - 0x18]
22cd46: call 0x3ff710
22cd4b: mov r9d, r14d
22cd4e: lea rdx, [rbp - 0x18]
22cd52: mov r8d, r14d
22cd55: lea rcx, [rbx + 0x2f0]
22cd5c: call 0x18aa40
22cd61: movzx eax, r14b
22cd65: jmp 0x22cc44
22cd6a: lea rdx, [rip + 0x36c51f] ; b'SHWater'
22cd71: lea rcx, [rsp + 0x60]
22cd76: call 0x3fd810
22cd7b: lea rdx, [rip + 0x3bea2b] ; b''
22cd82: lea rcx, [rsp + 0x50]
22cd87: call 0x3fd810
22cd8c: lea rdx, [rip + 0x3bea1a] ; b''
22cd93: lea rcx, [rsp + 0x58]
22cd98: call 0x3fd810
22cd9d: mov ecx, 0x418
22cda2: call 0x4f7a88
22cda7: mov rbx, rax
22cdaa: test rax, rax
22cdad: je 0x22c30e
22cdb3: mov rcx, rax
22cdb6: call 0x226910
22cdbb: lea rax, [rip + 0x36f5be] ; b'0\x81"@\x01'
22cdc2: lea rcx, [rbx + 0x1b8]
22cdc9: mov qword ptr [rbx], rax
22cdcc: call 0x410f70
22cdd1: lea rcx, [rbx + 0x2f0]
22cdd8: call 0x410d80
22cddd: lea rdx, [rsp + 0x60]
22cde2: lea rcx, [rbp - 0x20]
22cde6: call 0x3ff710
22cdeb: lea rcx, [rbx + 0x2c0]
22cdf2: mov r9d, r14d
22cdf5: mov r8d, r14d
22cdf8: lea rdx, [rbp - 0x20]
22cdfc: call 0x14d080
22ce01: mov rax, qword ptr [rsp + 0x50]
22ce06: cmp dword ptr [rax - 8], edi
22ce09: je 0x22cc42
22ce0f: lea rdx, [rsp + 0x50]
22ce14: lea rcx, [rbp - 0x18]
22ce18: call 0x3ff710
22ce1d: mov r9d, r14d
22ce20: lea rdx, [rbp - 0x18]
22ce24: mov r8d, r14d
22ce27: lea rcx, [rbx + 0x2f0]
22ce2e: call 0x18aa40
22ce33: movzx eax, r14b
22ce37: jmp 0x22cc44
22ce3c: lea rdx, [rip + 0x36c405] ; b'SHAir'
22ce43: lea rcx, [rsp + 0x60]
22ce48: call 0x3fd810
22ce4d: lea rdx, [rip + 0x36fa44] ; b'SHAir1'
22ce54: lea rcx, [rsp + 0x50]
22ce59: call 0x3fd810
22ce5e: lea rdx, [rip + 0x3be948] ; b''
22ce65: lea rcx, [rsp + 0x58]
22ce6a: call 0x3fd810
22ce6f: mov ecx, 0x418
22ce74: call 0x4f7a88
22ce79: mov rbx, rax
22ce7c: test rax, rax
22ce7f: je 0x22c30e
22ce85: mov rcx, rax
22ce88: call 0x226910
22ce8d: lea rax, [rip + 0x36f4ec] ; b'0\x81"@\x01'
22ce94: lea rcx, [rbx + 0x1b8]
22ce9b: mov qword ptr [rbx], rax
22ce9e: call 0x410f70
22cea3: lea rcx, [rbx + 0x2f0]
22ceaa: call 0x410d80
22ceaf: lea rdx, [rsp + 0x60]
22ceb4: lea rcx, [rbp - 0x20]
22ceb8: call 0x3ff710
22cebd: lea rcx, [rbx + 0x2c0]
22cec4: mov r9d, r14d
22cec7: mov r8d, r14d
22ceca: lea rdx, [rbp - 0x20]
22cece: call 0x14d080
22ced3: mov rax, qword ptr [rsp + 0x50]
22ced8: cmp dword ptr [rax - 8], edi
22cedb: je 0x22cc42
22cee1: lea rdx, [rsp + 0x50]
22cee6: lea rcx, [rbp - 0x18]
22ceea: call 0x3ff710
22ceef: mov r9d, r14d
22cef2: lea rdx, [rbp - 0x18]
22cef6: mov r8d, r14d
22cef9: lea rcx, [rbx + 0x2f0]
22cf00: call 0x18aa40
22cf05: movzx eax, r14b
22cf09: jmp 0x22cc44
22cf0e: lea rdx, [rip + 0x36c363] ; b'SHEarth'
22cf15: lea rcx, [rsp + 0x60]
22cf1a: call 0x3fd810
22cf1f: lea rdx, [rip + 0x36f97a] ; b'SHEarth1'
22cf26: lea rcx, [rsp + 0x50]
22cf2b: call 0x3fd810
22cf30: lea rdx, [rip + 0x3be876] ; b''
22cf37: lea rcx, [rsp + 0x58]
22cf3c: call 0x3fd810
22cf41: mov ecx, 0x418
22cf46: call 0x4f7a88
22cf4b: mov rbx, rax
22cf4e: test rax, rax
22cf51: je 0x22c30e
22cf57: mov rcx, rax
22cf5a: call 0x226910
22cf5f: lea rax, [rip + 0x36f41a] ; b'0\x81"@\x01'
22cf66: lea rcx, [rbx + 0x1b8]
22cf6d: mov qword ptr [rbx], rax
22cf70: call 0x410f70
22cf75: lea rcx, [rbx + 0x2f0]
22cf7c: call 0x410d80
22cf81: lea rdx, [rsp + 0x60]
22cf86: lea rcx, [rbp - 0x20]
22cf8a: call 0x3ff710
22cf8f: lea rcx, [rbx + 0x2c0]
22cf96: mov r9d, r14d
22cf99: mov r8d, r14d
22cf9c: lea rdx, [rbp - 0x20]
22cfa0: call 0x14d080
22cfa5: mov rax, qword ptr [rsp + 0x50]
22cfaa: cmp dword ptr [rax - 8], edi
22cfad: je 0x22cc42
22cfb3: lea rdx, [rsp + 0x50]
22cfb8: lea rcx, [rbp - 0x18]
22cfbc: call 0x3ff710
22cfc1: mov r9d, r14d
22cfc4: lea rdx, [rbp - 0x18]
22cfc8: mov r8d, r14d
22cfcb: lea rcx, [rbx + 0x2f0]
22cfd2: call 0x18aa40
22cfd7: movzx eax, r14b
22cfdb: jmp 0x22cc44
22cfe0: lea rdx, [rip + 0x36c2a9] ; b'SHWater'
22cfe7: lea rcx, [rsp + 0x60]
22cfec: call 0x3fd810
22cff1: lea rdx, [rip + 0x36f8b8] ; b'SHWater1'
22cff8: lea rcx, [rsp + 0x50]
22cffd: call 0x3fd810
22d002: lea rdx, [rip + 0x3be7a4] ; b''
22d009: lea rcx, [rsp + 0x58]
22d00e: call 0x3fd810
22d013: mov ecx, 0x418
22d018: call 0x4f7a88
22d01d: mov rbx, rax
22d020: test rax, rax
22d023: je 0x22c30e
22d029: mov rcx, rax
22d02c: call 0x226910
22d031: lea rax, [rip + 0x36f348] ; b'0\x81"@\x01'
22d038: lea rcx, [rbx + 0x1b8]
22d03f: mov qword ptr [rbx], rax
22d042: call 0x410f70
22d047: lea rcx, [rbx + 0x2f0]
22d04e: call 0x410d80
22d053: lea rdx, [rsp + 0x60]
22d058: lea rcx, [rbp - 0x20]
22d05c: call 0x3ff710
22d061: lea rcx, [rbx + 0x2c0]
22d068: mov r9d, r14d
22d06b: mov r8d, r14d
22d06e: lea rdx, [rbp - 0x20]
22d072: call 0x14d080
22d077: mov rax, qword ptr [rsp + 0x50]
22d07c: cmp dword ptr [rax - 8], edi
22d07f: je 0x22cc42
22d085: lea rdx, [rsp + 0x50]
22d08a: lea rcx, [rbp - 0x18]
22d08e: call 0x3ff710
22d093: mov r9d, r14d
22d096: lea rdx, [rbp - 0x18]
22d09a: mov r8d, r14d
22d09d: lea rcx, [rbx + 0x2f0]
22d0a4: call 0x18aa40
22d0a9: movzx eax, r14b
22d0ad: jmp 0x22cc44
22d0b2: lea rdx, [rip + 0x36c18f] ; b'SHAir'
22d0b9: lea rcx, [rsp + 0x60]
22d0be: call 0x3fd810
22d0c3: lea rdx, [rip + 0x36f7f2] ; b'SHAir2'
22d0ca: lea rcx, [rsp + 0x50]
22d0cf: call 0x3fd810
22d0d4: lea rdx, [rip + 0x3be6d2] ; b''
22d0db: lea rcx, [rsp + 0x58]
22d0e0: call 0x3fd810
22d0e5: mov ecx, 0x418
22d0ea: call 0x4f7a88
22d0ef: mov rbx, rax
22d0f2: test rax, rax
22d0f5: je 0x22c30e
22d0fb: mov rcx, rax
22d0fe: call 0x226910
22d103: lea rax, [rip + 0x36f276] ; b'0\x81"@\x01'
22d10a: lea rcx, [rbx + 0x1b8]
22d111: mov qword ptr [rbx], rax
22d114: call 0x410f70
22d119: lea rcx, [rbx + 0x2f0]
22d120: call 0x410d80
22d125: lea rdx, [rsp + 0x60]
22d12a: lea rcx, [rbp - 0x20]
22d12e: call 0x3ff710
22d133: lea rcx, [rbx + 0x2c0]
22d13a: mov r9d, r14d
22d13d: mov r8d, r14d
22d140: lea rdx, [rbp - 0x20]
22d144: call 0x14d080
22d149: mov rax, qword ptr [rsp + 0x50]
22d14e: cmp dword ptr [rax - 8], edi
22d151: je 0x22cc42
22d157: lea rdx, [rsp + 0x50]
22d15c: lea rcx, [rbp - 0x18]
22d160: call 0x3ff710
22d165: mov r9d, r14d
22d168: lea rdx, [rbp - 0x18]
22d16c: mov r8d, r14d
22d16f: lea rcx, [rbx + 0x2f0]
22d176: call 0x18aa40
22d17b: movzx eax, r14b
22d17f: jmp 0x22cc44
22d184: lea rdx, [rip + 0x36c0ed] ; b'SHEarth'
22d18b: lea rcx, [rsp + 0x60]
22d190: call 0x3fd810
22d195: lea rdx, [rip + 0x36f72c] ; b'SHEarth2'
22d19c: lea rcx, [rsp + 0x50]
22d1a1: call 0x3fd810
22d1a6: lea rdx, [rip + 0x3be600] ; b''
22d1ad: lea rcx, [rsp + 0x58]
22d1b2: call 0x3fd810
22d1b7: mov ecx, 0x418
22d1bc: call 0x4f7a88
22d1c1: mov rbx, rax
22d1c4: test rax, rax
22d1c7: je 0x22c30e
22d1cd: mov rcx, rax
22d1d0: call 0x226910
22d1d5: lea rax, [rip + 0x36f1a4] ; b'0\x81"@\x01'
22d1dc: lea rcx, [rbx + 0x1b8]
22d1e3: mov qword ptr [rbx], rax
22d1e6: call 0x410f70
22d1eb: lea rcx, [rbx + 0x2f0]
22d1f2: call 0x410d80
22d1f7: lea rdx, [rsp + 0x60]
22d1fc: lea rcx, [rbp - 0x20]
22d200: call 0x3ff710
22d205: lea rcx, [rbx + 0x2c0]
22d20c: mov r9d, r14d
22d20f: mov r8d, r14d
22d212: lea rdx, [rbp - 0x20]
22d216: call 0x14d080
22d21b: mov rax, qword ptr [rsp + 0x50]
22d220: cmp dword ptr [rax - 8], edi
22d223: je 0x22cc42
22d229: lea rdx, [rsp + 0x50]
22d22e: lea rcx, [rbp - 0x18]
22d232: call 0x3ff710
22d237: mov r9d, r14d
22d23a: lea rdx, [rbp - 0x18]
22d23e: mov r8d, r14d
22d241: lea rcx, [rbx + 0x2f0]
22d248: call 0x18aa40
22d24d: movzx eax, r14b
22d251: jmp 0x22cc44
22d256: lea rdx, [rip + 0x36c033] ; b'SHWater'
22d25d: lea rcx, [rsp + 0x60]
22d262: call 0x3fd810
22d267: lea rdx, [rip + 0x36f66a] ; b'SHWater2'
22d26e: lea rcx, [rsp + 0x50]
22d273: call 0x3fd810
22d278: lea rdx, [rip + 0x3be52e] ; b''
22d27f: lea rcx, [rsp + 0x58]
22d284: call 0x3fd810
22d289: mov ecx, 0x418
22d28e: call 0x4f7a88
22d293: mov rbx, rax
22d296: test rax, rax
22d299: je 0x22c30e
22d29f: mov rcx, rax
22d2a2: call 0x226910
22d2a7: lea rax, [rip + 0x36f0d2] ; b'0\x81"@\x01'
22d2ae: lea rcx, [rbx + 0x1b8]
22d2b5: mov qword ptr [rbx], rax
22d2b8: call 0x410f70
22d2bd: lea rcx, [rbx + 0x2f0]
22d2c4: call 0x410d80
22d2c9: lea rdx, [rsp + 0x60]
22d2ce: lea rcx, [rbp - 0x20]
22d2d2: call 0x3ff710
22d2d7: lea rcx, [rbx + 0x2c0]
22d2de: mov r9d, r14d
22d2e1: mov r8d, r14d
22d2e4: lea rdx, [rbp - 0x20]
22d2e8: call 0x14d080
22d2ed: mov rax, qword ptr [rsp + 0x50]
22d2f2: cmp dword ptr [rax - 8], edi
22d2f5: je 0x22cc42
22d2fb: lea rdx, [rsp + 0x50]
22d300: lea rcx, [rbp - 0x18]
22d304: call 0x3ff710
22d309: mov r9d, r14d
22d30c: lea rdx, [rbp - 0x18]
22d310: mov r8d, r14d
22d313: lea rcx, [rbx + 0x2f0]
22d31a: call 0x18aa40
22d31f: movzx eax, r14b
22d323: jmp 0x22cc44
22d328: lea rdx, [rip + 0x36bf19] ; b'SHAir'
22d32f: lea rcx, [rsp + 0x60]
22d334: call 0x3fd810
22d339: lea rdx, [rip + 0x36f5a4] ; b'SHAir3'
22d340: lea rcx, [rsp + 0x50]
22d345: call 0x3fd810
22d34a: lea rdx, [rip + 0x3be45c] ; b''
22d351: lea rcx, [rsp + 0x58]
22d356: call 0x3fd810
22d35b: mov ecx, 0x418
22d360: call 0x4f7a88
22d365: mov rbx, rax
22d368: test rax, rax
22d36b: je 0x22c30e
22d371: mov rcx, rax
22d374: call 0x226910
22d379: lea rax, [rip + 0x36f000] ; b'0\x81"@\x01'
22d380: lea rcx, [rbx + 0x1b8]
22d387: mov qword ptr [rbx], rax
22d38a: call 0x410f70
22d38f: lea rcx, [rbx + 0x2f0]
22d396: call 0x410d80
22d39b: lea rdx, [rsp + 0x60]
22d3a0: lea rcx, [rbp - 0x20]
22d3a4: call 0x3ff710
22d3a9: lea rcx, [rbx + 0x2c0]
22d3b0: mov r9d, r14d
22d3b3: mov r8d, r14d
22d3b6: lea rdx, [rbp - 0x20]
22d3ba: call 0x14d080
22d3bf: mov rax, qword ptr [rsp + 0x50]
22d3c4: cmp dword ptr [rax - 8], edi
22d3c7: je 0x22cc42
22d3cd: lea rdx, [rsp + 0x50]
22d3d2: lea rcx, [rbp - 0x18]
22d3d6: call 0x3ff710
22d3db: mov r9d, r14d
22d3de: lea rdx, [rbp - 0x18]
22d3e2: mov r8d, r14d
22d3e5: lea rcx, [rbx + 0x2f0]
22d3ec: call 0x18aa40
22d3f1: movzx eax, r14b
22d3f5: jmp 0x22cc44
22d3fa: lea rdx, [rip + 0x36be77] ; b'SHEarth'
22d401: lea rcx, [rsp + 0x60]
22d406: call 0x3fd810
22d40b: lea rdx, [rip + 0x36f4de] ; b'SHEarth3'
22d412: lea rcx, [rsp + 0x50]
22d417: call 0x3fd810
22d41c: lea rdx, [rip + 0x3be38a] ; b''
22d423: lea rcx, [rsp + 0x58]
22d428: call 0x3fd810
22d42d: mov ecx, 0x418
22d432: call 0x4f7a88
22d437: mov rbx, rax
22d43a: test rax, rax
22d43d: je 0x22c30e
22d443: mov rcx, rax
22d446: call 0x226910
22d44b: lea rax, [rip + 0x36ef2e] ; b'0\x81"@\x01'
22d452: lea rcx, [rbx + 0x1b8]
22d459: mov qword ptr [rbx], rax
22d45c: call 0x410f70
22d461: lea rcx, [rbx + 0x2f0]
22d468: call 0x410d80
22d46d: lea rdx, [rsp + 0x60]
22d472: lea rcx, [rbp - 0x20]
22d476: call 0x3ff710
22d47b: lea rcx, [rbx + 0x2c0]
22d482: mov r9d, r14d
22d485: mov r8d, r14d
22d488: lea rdx, [rbp - 0x20]
22d48c: call 0x14d080
22d491: mov rax, qword ptr [rsp + 0x50]
22d496: cmp dword ptr [rax - 8], edi
22d499: je 0x22cc42
22d49f: lea rdx, [rsp + 0x50]
22d4a4: lea rcx, [rbp - 0x18]
22d4a8: call 0x3ff710
22d4ad: mov r9d, r14d
22d4b0: lea rdx, [rbp - 0x18]
22d4b4: mov r8d, r14d
22d4b7: lea rcx, [rbx + 0x2f0]
22d4be: call 0x18aa40
22d4c3: movzx eax, r14b
22d4c7: jmp 0x22cc44
22d4cc: lea rdx, [rip + 0x36bdbd] ; b'SHWater'
22d4d3: lea rcx, [rsp + 0x60]
22d4d8: call 0x3fd810
22d4dd: lea rdx, [rip + 0x36f41c] ; b'SHWater3'
22d4e4: lea rcx, [rsp + 0x50]
22d4e9: call 0x3fd810
22d4ee: lea rdx, [rip + 0x3be2b8] ; b''
22d4f5: lea rcx, [rsp + 0x58]
22d4fa: call 0x3fd810
22d4ff: mov ecx, 0x418
22d504: call 0x4f7a88
22d509: mov rbx, rax
22d50c: test rax, rax
22d50f: je 0x22c30e
22d515: mov rcx, rax
22d518: call 0x226910
22d51d: lea rax, [rip + 0x36ee5c] ; b'0\x81"@\x01'
22d524: lea rcx, [rbx + 0x1b8]
22d52b: mov qword ptr [rbx], rax
22d52e: call 0x410f70
22d533: lea rcx, [rbx + 0x2f0]
22d53a: call 0x410d80
22d53f: lea rdx, [rsp + 0x60]
22d544: lea rcx, [rbp - 0x20]
22d548: call 0x3ff710
22d54d: lea rcx, [rbx + 0x2c0]
22d554: mov r9d, r14d
22d557: mov r8d, r14d
22d55a: lea rdx, [rbp - 0x20]
22d55e: call 0x14d080
22d563: mov rax, qword ptr [rsp + 0x50]
22d568: cmp dword ptr [rax - 8], edi
22d56b: je 0x22cc42
22d571: lea rdx, [rsp + 0x50]
22d576: lea rcx, [rbp - 0x18]
22d57a: call 0x3ff710
22d57f: mov r9d, r14d
22d582: lea rdx, [rbp - 0x18]
22d586: mov r8d, r14d
22d589: lea rcx, [rbx + 0x2f0]
22d590: call 0x18aa40
22d595: movzx eax, r14b
22d599: jmp 0x22cc44
22d59e: lea rdx, [rip + 0x36bca3] ; b'SHAir'
22d5a5: lea rcx, [rsp + 0x60]
22d5aa: call 0x3fd810
22d5af: lea rdx, [rip + 0x36f356] ; b'SHAir4'
22d5b6: lea rcx, [rsp + 0x50]
22d5bb: call 0x3fd810
22d5c0: lea rdx, [rip + 0x3be1e6] ; b''
22d5c7: lea rcx, [rsp + 0x58]
22d5cc: call 0x3fd810
22d5d1: mov ecx, 0x418
22d5d6: call 0x4f7a88
22d5db: mov rbx, rax
22d5de: test rax, rax
22d5e1: je 0x22c30e
22d5e7: mov rcx, rax
22d5ea: call 0x226910
22d5ef: lea rax, [rip + 0x36ed8a] ; b'0\x81"@\x01'
22d5f6: lea rcx, [rbx + 0x1b8]
22d5fd: mov qword ptr [rbx], rax
22d600: call 0x410f70
22d605: lea rcx, [rbx + 0x2f0]
22d60c: call 0x410d80
22d611: lea rdx, [rsp + 0x60]
22d616: lea rcx, [rbp - 0x20]
22d61a: call 0x3ff710
22d61f: lea rcx, [rbx + 0x2c0]
22d626: mov r9d, r14d
22d629: mov r8d, r14d
22d62c: lea rdx, [rbp - 0x20]
22d630: call 0x14d080
22d635: mov rax, qword ptr [rsp + 0x50]
22d63a: cmp dword ptr [rax - 8], edi
22d63d: je 0x22cc42
22d643: lea rdx, [rsp + 0x50]
22d648: lea rcx, [rbp - 0x18]
22d64c: call 0x3ff710
22d651: mov r9d, r14d
22d654: lea rdx, [rbp - 0x18]
22d658: mov r8d, r14d
22d65b: lea rcx, [rbx + 0x2f0]
22d662: call 0x18aa40
22d667: movzx eax, r14b
22d66b: jmp 0x22cc44
22d670: lea rdx, [rip + 0x36bc01] ; b'SHEarth'
22d677: lea rcx, [rsp + 0x60]
22d67c: call 0x3fd810
22d681: lea rdx, [rip + 0x36f290] ; b'SHEarth4'
22d688: lea rcx, [rsp + 0x50]
22d68d: call 0x3fd810
22d692: lea rdx, [rip + 0x3be114] ; b''
22d699: lea rcx, [rsp + 0x58]
22d69e: call 0x3fd810
22d6a3: mov ecx, 0x418
22d6a8: call 0x4f7a88
22d6ad: mov rbx, rax
22d6b0: test rax, rax
22d6b3: je 0x22c30e
22d6b9: mov rcx, rax
22d6bc: call 0x226910
22d6c1: lea rax, [rip + 0x36ecb8] ; b'0\x81"@\x01'
22d6c8: lea rcx, [rbx + 0x1b8]
22d6cf: mov qword ptr [rbx], rax
22d6d2: call 0x410f70
22d6d7: lea rcx, [rbx + 0x2f0]
22d6de: call 0x410d80
22d6e3: lea rdx, [rsp + 0x60]
22d6e8: lea rcx, [rbp - 0x20]
22d6ec: call 0x3ff710
22d6f1: lea rcx, [rbx + 0x2c0]
22d6f8: mov r9d, r14d
22d6fb: mov r8d, r14d
22d6fe: lea rdx, [rbp - 0x20]
22d702: call 0x14d080
22d707: mov rax, qword ptr [rsp + 0x50]
22d70c: cmp dword ptr [rax - 8], edi
22d70f: je 0x22cc42
22d715: lea rdx, [rsp + 0x50]
22d71a: lea rcx, [rbp - 0x18]
22d71e: call 0x3ff710
22d723: mov r9d, r14d
22d726: lea rdx, [rbp - 0x18]
22d72a: mov r8d, r14d
22d72d: lea rcx, [rbx + 0x2f0]
22d734: call 0x18aa40
22d739: movzx eax, r14b
22d73d: jmp 0x22cc44
22d742: lea rdx, [rip + 0x36bb47] ; b'SHWater'
22d749: lea rcx, [rsp + 0x60]
22d74e: call 0x3fd810
22d753: lea rdx, [rip + 0x36f1ce] ; b'SHWater4'
22d75a: lea rcx, [rsp + 0x50]
22d75f: call 0x3fd810
22d764: lea rdx, [rip + 0x3be042] ; b''
22d76b: lea rcx, [rsp + 0x58]
22d770: call 0x3fd810
22d775: mov ecx, 0x418
22d77a: call 0x4f7a88
22d77f: mov rbx, rax
22d782: test rax, rax
22d785: je 0x22c30e
22d78b: mov rcx, rax
22d78e: call 0x226910
22d793: lea rax, [rip + 0x36ebe6] ; b'0\x81"@\x01'
22d79a: lea rcx, [rbx + 0x1b8]
22d7a1: mov qword ptr [rbx], rax
22d7a4: call 0x410f70
22d7a9: lea rcx, [rbx + 0x2f0]
22d7b0: call 0x410d80
22d7b5: lea rdx, [rsp + 0x60]
22d7ba: lea rcx, [rbp - 0x20]
22d7be: call 0x3ff710
22d7c3: lea rcx, [rbx + 0x2c0]
22d7ca: mov r9d, r14d
22d7cd: mov r8d, r14d
22d7d0: lea rdx, [rbp - 0x20]
22d7d4: call 0x14d080
22d7d9: mov rax, qword ptr [rsp + 0x50]
22d7de: cmp dword ptr [rax - 8], edi
22d7e1: je 0x22cc42
22d7e7: lea rdx, [rsp + 0x50]
22d7ec: lea rcx, [rbp - 0x18]
22d7f0: call 0x3ff710
22d7f5: mov r9d, r14d
22d7f8: lea rdx, [rbp - 0x18]
22d7fc: mov r8d, r14d
22d7ff: lea rcx, [rbx + 0x2f0]
22d806: call 0x18aa40
22d80b: movzx eax, r14b
22d80f: jmp 0x22cc44
22d814: lea rdx, [rip + 0x36ba2d] ; b'SHAir'
22d81b: lea rcx, [rsp + 0x60]
22d820: call 0x3fd810
22d825: lea rdx, [rip + 0x36f108] ; b'SHAir5'
22d82c: lea rcx, [rsp + 0x50]
22d831: call 0x3fd810
22d836: lea rdx, [rip + 0x3bdf70] ; b''
22d83d: lea rcx, [rsp + 0x58]
22d842: call 0x3fd810
22d847: mov ecx, 0x418
22d84c: call 0x4f7a88
22d851: mov rbx, rax
22d854: test rax, rax
22d857: je 0x22c30e
22d85d: mov rcx, rax
22d860: call 0x226910
22d865: lea rax, [rip + 0x36eb14] ; b'0\x81"@\x01'
22d86c: lea rcx, [rbx + 0x1b8]
22d873: mov qword ptr [rbx], rax
22d876: call 0x410f70
22d87b: lea rcx, [rbx + 0x2f0]
22d882: call 0x410d80
22d887: lea rdx, [rsp + 0x60]
22d88c: lea rcx, [rbp - 0x20]
22d890: call 0x3ff710
22d895: lea rcx, [rbx + 0x2c0]
22d89c: mov r9d, r14d
22d89f: mov r8d, r14d
22d8a2: lea rdx, [rbp - 0x20]
22d8a6: call 0x14d080
22d8ab: mov rax, qword ptr [rsp + 0x50]
22d8b0: cmp dword ptr [rax - 8], edi
22d8b3: je 0x22cc42
22d8b9: lea rdx, [rsp + 0x50]
22d8be: lea rcx, [rbp - 0x18]
22d8c2: call 0x3ff710
22d8c7: mov r9d, r14d
22d8ca: lea rdx, [rbp - 0x18]
22d8ce: mov r8d, r14d
22d8d1: lea rcx, [rbx + 0x2f0]
22d8d8: call 0x18aa40
22d8dd: movzx eax, r14b
22d8e1: jmp 0x22cc44
22d8e6: lea rdx, [rip + 0x36b98b] ; b'SHEarth'
22d8ed: lea rcx, [rsp + 0x60]
22d8f2: call 0x3fd810
22d8f7: lea rdx, [rip + 0x36f042] ; b'SHEarth5'
22d8fe: lea rcx, [rsp + 0x50]
22d903: call 0x3fd810
22d908: lea rdx, [rip + 0x3bde9e] ; b''
22d90f: lea rcx, [rsp + 0x58]
22d914: call 0x3fd810
22d919: mov ecx, 0x418
22d91e: call 0x4f7a88
22d923: mov rbx, rax
22d926: test rax, rax
22d929: je 0x22da04
22d92f: mov rcx, rax
22d932: call 0x226910
22d937: lea rax, [rip + 0x36ea42] ; b'0\x81"@\x01'
22d93e: lea rcx, [rbx + 0x1b8]
22d945: mov qword ptr [rbx], rax
22d948: call 0x410f70
22d94d: lea rcx, [rbx + 0x2f0]
22d954: call 0x410d80
22d959: lea rdx, [rsp + 0x60]
22d95e: lea rcx, [rbp - 0x20]
22d962: call 0x3ff710
22d967: lea rcx, [rbx + 0x2c0]
22d96e: mov r9d, r14d
22d971: mov r8d, r14d
22d974: lea rdx, [rbp - 0x20]
22d978: call 0x14d080
22d97d: mov rax, qword ptr [rsp + 0x50]
22d982: cmp dword ptr [rax - 8], edi
22d985: je 0x22d9b1
22d987: lea rdx, [rsp + 0x50]
22d98c: lea rcx, [rbp - 0x18]
22d990: call 0x3ff710
22d995: mov r9d, r14d
22d998: lea rdx, [rbp - 0x18]
22d99c: mov r8d, r14d
22d99f: lea rcx, [rbx + 0x2f0]
22d9a6: call 0x18aa40
22d9ab: movzx eax, r14b
22d9af: jmp 0x22d9b3
22d9b1: xor al, al
22d9b3: xor edx, edx
22d9b5: mov byte ptr [rbx + 0x414], al
22d9bb: lea rcx, [rbx + 0x1b8]
22d9c2: call 0x412380
22d9c7: xor edx, edx
22d9c9: lea rcx, [rbx + 0x1b8]
22d9d0: call 0x411610
22d9d5: lea rcx, [rbx + 0x140]
22d9dc: lea r8, [rsp + 0x58]
22d9e1: lea rdx, [rbp - 0x10]
22d9e5: call 0x3ff890
22d9ea: mov dword ptr [rbx + 0x410], 8
22d9f4: mov byte ptr [rbx + 0x415], dil
22d9fb: mov byte ptr [rbx + 0x158], r14b
22da02: jmp 0x22da06
22da04: xor ebx, ebx
22da06: lea rcx, [rbx + 0x140]
22da0d: lea r8, [rip + 0x3bdd99] ; b''
22da14: lea rdx, [rbp - 0x20]
22da18: call 0x3ff960
22da1d: lea rdx, [rbp - 0x18]
22da21: jmp 0x22e8d9
22da26: lea rdx, [rip + 0x36b863] ; b'SHWater'
22da2d: lea rcx, [rsp + 0x60]
22da32: call 0x3fd810
22da37: lea rdx, [rip + 0x36ef12] ; b'SHWater5'
22da3e: lea rcx, [rsp + 0x50]
22da43: call 0x3fd810
22da48: lea rdx, [rip + 0x3bdd5e] ; b''
22da4f: lea rcx, [rsp + 0x58]
22da54: call 0x3fd810
22da59: mov ecx, 0x418
22da5e: call 0x4f7a88
22da63: mov rbx, rax
22da66: test rax, rax
22da69: je 0x22da04
22da6b: mov rcx, rax
22da6e: call 0x226910
22da73: lea rax, [rip + 0x36e906] ; b'0\x81"@\x01'
22da7a: lea rcx, [rbx + 0x1b8]
22da81: mov qword ptr [rbx], rax
22da84: call 0x410f70
22da89: lea rcx, [rbx + 0x2f0]
22da90: call 0x410d80
22da95: lea rdx, [rsp + 0x60]
22da9a: lea rcx, [rbp - 0x20]
22da9e: call 0x3ff710
22daa3: lea rcx, [rbx + 0x2c0]
22daaa: mov r9d, r14d
22daad: mov r8d, r14d
22dab0: lea rdx, [rbp - 0x20]
22dab4: call 0x14d080
22dab9: mov rax, qword ptr [rsp + 0x50]
22dabe: cmp dword ptr [rax - 8], edi
22dac1: je 0x22d9b1
22dac7: lea rdx, [rsp + 0x50]
22dacc: lea rcx, [rbp - 0x18]
22dad0: call 0x3ff710
22dad5: mov r9d, r14d
22dad8: lea rdx, [rbp - 0x18]
22dadc: mov r8d, r14d
22dadf: lea rcx, [rbx + 0x2f0]
22dae6: call 0x18aa40
22daeb: movzx eax, r14b
22daef: jmp 0x22d9b3
22daf4: lea rdx, [rip + 0x36b74d] ; b'SHAir'
22dafb: lea rcx, [rsp + 0x60]
22db00: call 0x3fd810
22db05: lea rdx, [rip + 0x36ee50] ; b'SHAir6'
22db0c: lea rcx, [rsp + 0x50]
22db11: call 0x3fd810
22db16: lea rdx, [rip + 0x3bdc90] ; b''
22db1d: lea rcx, [rsp + 0x58]
22db22: call 0x3fd810
22db27: mov ecx, 0x418
22db2c: call 0x4f7a88
22db31: mov rbx, rax
22db34: test rax, rax
22db37: je 0x22da04
22db3d: mov rcx, rax
22db40: call 0x226910
22db45: lea rax, [rip + 0x36e834] ; b'0\x81"@\x01'
22db4c: lea rcx, [rbx + 0x1b8]
22db53: mov qword ptr [rbx], rax
22db56: call 0x410f70
22db5b: lea rcx, [rbx + 0x2f0]
22db62: call 0x410d80
22db67: lea rdx, [rsp + 0x60]
22db6c: lea rcx, [rbp - 0x20]
22db70: call 0x3ff710
22db75: lea rcx, [rbx + 0x2c0]
22db7c: mov r9d, r14d
22db7f: mov r8d, r14d
22db82: lea rdx, [rbp - 0x20]
22db86: call 0x14d080
22db8b: mov rax, qword ptr [rsp + 0x50]
22db90: cmp dword ptr [rax - 8], edi
22db93: je 0x22d9b1
22db99: lea rdx, [rsp + 0x50]
22db9e: lea rcx, [rbp - 0x18]
22dba2: call 0x3ff710
22dba7: mov r9d, r14d
22dbaa: lea rdx, [rbp - 0x18]
22dbae: mov r8d, r14d
22dbb1: lea rcx, [rbx + 0x2f0]
22dbb8: call 0x18aa40
22dbbd: movzx eax, r14b
22dbc1: jmp 0x22d9b3
22dbc6: lea rdx, [rip + 0x36b6ab] ; b'SHEarth'
22dbcd: lea rcx, [rsp + 0x60]
22dbd2: call 0x3fd810
22dbd7: lea rdx, [rip + 0x36ed8a] ; b'SHEarth6'
22dbde: lea rcx, [rsp + 0x50]
22dbe3: call 0x3fd810
22dbe8: lea rdx, [rip + 0x3bdbbe] ; b''
22dbef: lea rcx, [rsp + 0x58]
22dbf4: call 0x3fd810
22dbf9: mov ecx, 0x418
22dbfe: call 0x4f7a88
22dc03: mov rbx, rax
22dc06: test rax, rax
22dc09: je 0x22da04
22dc0f: mov rcx, rax
22dc12: call 0x226910
22dc17: lea rax, [rip + 0x36e762] ; b'0\x81"@\x01'
22dc1e: lea rcx, [rbx + 0x1b8]
22dc25: mov qword ptr [rbx], rax
22dc28: call 0x410f70
22dc2d: lea rcx, [rbx + 0x2f0]
22dc34: call 0x410d80
22dc39: lea rdx, [rsp + 0x60]
22dc3e: lea rcx, [rbp - 0x20]
22dc42: call 0x3ff710
22dc47: lea rcx, [rbx + 0x2c0]
22dc4e: mov r9d, r14d
22dc51: mov r8d, r14d
22dc54: lea rdx, [rbp - 0x20]
22dc58: call 0x14d080
22dc5d: mov rax, qword ptr [rsp + 0x50]
22dc62: cmp dword ptr [rax - 8], edi
22dc65: je 0x22d9b1
22dc6b: lea rdx, [rsp + 0x50]
22dc70: lea rcx, [rbp - 0x18]
22dc74: call 0x3ff710
22dc79: mov r9d, r14d
22dc7c: lea rdx, [rbp - 0x18]
22dc80: mov r8d, r14d
22dc83: lea rcx, [rbx + 0x2f0]
22dc8a: call 0x18aa40
22dc8f: movzx eax, r14b
22dc93: jmp 0x22d9b3
22dc98: lea rdx, [rip + 0x36b5f1] ; b'SHWater'
22dc9f: lea rcx, [rsp + 0x60]
22dca4: call 0x3fd810
22dca9: lea rdx, [rip + 0x36ecc8] ; b'SHWater6'
22dcb0: lea rcx, [rsp + 0x50]
22dcb5: call 0x3fd810
22dcba: lea rdx, [rip + 0x3bdaec] ; b''
22dcc1: lea rcx, [rsp + 0x58]
22dcc6: call 0x3fd810
22dccb: mov ecx, 0x418
22dcd0: call 0x4f7a88
22dcd5: mov rbx, rax
22dcd8: test rax, rax
22dcdb: je 0x22da04
22dce1: mov rcx, rax
22dce4: call 0x226910
22dce9: lea rax, [rip + 0x36e690] ; b'0\x81"@\x01'
22dcf0: lea rcx, [rbx + 0x1b8]
22dcf7: mov qword ptr [rbx], rax
22dcfa: call 0x410f70
22dcff: lea rcx, [rbx + 0x2f0]
22dd06: call 0x410d80
22dd0b: lea rdx, [rsp + 0x60]
22dd10: lea rcx, [rbp - 0x20]
22dd14: call 0x3ff710
22dd19: lea rcx, [rbx + 0x2c0]
22dd20: mov r9d, r14d
22dd23: mov r8d, r14d
22dd26: lea rdx, [rbp - 0x20]
22dd2a: call 0x14d080
22dd2f: mov rax, qword ptr [rsp + 0x50]
22dd34: cmp dword ptr [rax - 8], edi
22dd37: je 0x22d9b1
22dd3d: lea rdx, [rsp + 0x50]
22dd42: lea rcx, [rbp - 0x18]
22dd46: call 0x3ff710
22dd4b: mov r9d, r14d
22dd4e: lea rdx, [rbp - 0x18]
22dd52: mov r8d, r14d
22dd55: lea rcx, [rbx + 0x2f0]
22dd5c: call 0x18aa40
22dd61: movzx eax, r14b
22dd65: jmp 0x22d9b3
22dd6a: lea rdx, [rip + 0x36b4d7] ; b'SHAir'
22dd71: lea rcx, [rsp + 0x60]
22dd76: call 0x3fd810
22dd7b: lea rdx, [rip + 0x36b4ce] ; b'SHAir7'
22dd82: lea rcx, [rsp + 0x50]
22dd87: call 0x3fd810
22dd8c: lea rdx, [rip + 0x3bda1a] ; b''
22dd93: lea rcx, [rsp + 0x58]
22dd98: call 0x3fd810
22dd9d: mov ecx, 0x418
22dda2: call 0x4f7a88
22dda7: mov rbx, rax
22ddaa: test rax, rax
22ddad: je 0x22da04
22ddb3: mov rcx, rax
22ddb6: call 0x226910
22ddbb: lea rax, [rip + 0x36e5be] ; b'0\x81"@\x01'
22ddc2: lea rcx, [rbx + 0x1b8]
22ddc9: mov qword ptr [rbx], rax
22ddcc: call 0x410f70
22ddd1: lea rcx, [rbx + 0x2f0]
22ddd8: call 0x410d80
22dddd: lea rdx, [rsp + 0x60]
22dde2: lea rcx, [rbp - 0x20]
22dde6: call 0x3ff710
22ddeb: lea rcx, [rbx + 0x2c0]
22ddf2: mov r9d, r14d
22ddf5: mov r8d, r14d
22ddf8: lea rdx, [rbp - 0x20]
22ddfc: call 0x14d080
22de01: mov rax, qword ptr [rsp + 0x50]
22de06: cmp dword ptr [rax - 8], edi
22de09: je 0x22d9b1
22de0f: lea rdx, [rsp + 0x50]
22de14: lea rcx, [rbp - 0x18]
22de18: call 0x3ff710
22de1d: mov r9d, r14d
22de20: lea rdx, [rbp - 0x18]
22de24: mov r8d, r14d
22de27: lea rcx, [rbx + 0x2f0]
22de2e: call 0x18aa40
22de33: movzx eax, r14b
22de37: jmp 0x22d9b3
22de3c: lea rdx, [rip + 0x36b435] ; b'SHEarth'
22de43: lea rcx, [rsp + 0x60]
22de48: call 0x3fd810
22de4d: lea rdx, [rip + 0x36eb34] ; b'SHEarth7'
22de54: lea rcx, [rsp + 0x50]
22de59: call 0x3fd810
22de5e: lea rdx, [rip + 0x3bd948] ; b''
22de65: lea rcx, [rsp + 0x58]
22de6a: call 0x3fd810
22de6f: mov ecx, 0x418
22de74: call 0x4f7a88
22de79: mov rbx, rax
22de7c: test rax, rax
22de7f: je 0x22da04
22de85: mov rcx, rax
22de88: call 0x226910
22de8d: lea rax, [rip + 0x36e4ec] ; b'0\x81"@\x01'
22de94: lea rcx, [rbx + 0x1b8]
22de9b: mov qword ptr [rbx], rax
22de9e: call 0x410f70
22dea3: lea rcx, [rbx + 0x2f0]
22deaa: call 0x410d80
22deaf: lea rdx, [rsp + 0x60]
22deb4: lea rcx, [rbp - 0x20]
22deb8: call 0x3ff710
22debd: lea rcx, [rbx + 0x2c0]
22dec4: mov r9d, r14d
22dec7: mov r8d, r14d
22deca: lea rdx, [rbp - 0x20]
22dece: call 0x14d080
22ded3: mov rax, qword ptr [rsp + 0x50]
22ded8: cmp dword ptr [rax - 8], edi
22dedb: je 0x22d9b1
22dee1: lea rdx, [rsp + 0x50]
22dee6: lea rcx, [rbp - 0x18]
22deea: call 0x3ff710
22deef: mov r9d, r14d
22def2: lea rdx, [rbp - 0x18]
22def6: mov r8d, r14d
22def9: lea rcx, [rbx + 0x2f0]
22df00: call 0x18aa40
22df05: movzx eax, r14b
22df09: jmp 0x22d9b3
22df0e: lea rdx, [rip + 0x36b37b] ; b'SHWater'
22df15: lea rcx, [rsp + 0x60]
22df1a: call 0x3fd810
22df1f: lea rdx, [rip + 0x36ea72] ; b'SHWater7'
22df26: lea rcx, [rsp + 0x50]
22df2b: call 0x3fd810
22df30: lea rdx, [rip + 0x3bd876] ; b''
22df37: lea rcx, [rsp + 0x58]
22df3c: call 0x3fd810
22df41: mov ecx, 0x418
22df46: call 0x4f7a88
22df4b: mov rbx, rax
22df4e: test rax, rax
22df51: je 0x22da04
22df57: mov rcx, rax
22df5a: call 0x226910
22df5f: lea rax, [rip + 0x36e41a] ; b'0\x81"@\x01'
22df66: lea rcx, [rbx + 0x1b8]
22df6d: mov qword ptr [rbx], rax
22df70: call 0x410f70
22df75: lea rcx, [rbx + 0x2f0]
22df7c: call 0x410d80
22df81: lea rdx, [rsp + 0x60]
22df86: lea rcx, [rbp - 0x20]
22df8a: call 0x3ff710
22df8f: lea rcx, [rbx + 0x2c0]
22df96: mov r9d, r14d
22df99: mov r8d, r14d
22df9c: lea rdx, [rbp - 0x20]
22dfa0: call 0x14d080
22dfa5: mov rax, qword ptr [rsp + 0x50]
22dfaa: cmp dword ptr [rax - 8], edi
22dfad: je 0x22d9b1
22dfb3: lea rdx, [rsp + 0x50]
22dfb8: lea rcx, [rbp - 0x18]
22dfbc: call 0x3ff710
22dfc1: mov r9d, r14d
22dfc4: lea rdx, [rbp - 0x18]
22dfc8: mov r8d, r14d
22dfcb: lea rcx, [rbx + 0x2f0]
22dfd2: call 0x18aa40
22dfd7: movzx eax, r14b
22dfdb: jmp 0x22d9b3
22dfe0: mov ecx, 0x3b8
22dfe5: call 0x4f7a88
22dfea: test rax, rax
22dfed: je 0x22dffa
22dfef: mov rcx, rax
22dff2: call 0x227b10
22dff7: mov rbx, rax
22dffa: xor edx, edx
22dffc: mov word ptr [rbx + 0x214], r14w
22e004: mov rcx, rbx
22e007: lea r8d, [rdx + 0x43]
22e00b: call 0x235d80
22e010: jmp 0x22da06
22e015: mov ecx, 0x3b8
22e01a: call 0x4f7a88
22e01f: test rax, rax
22e022: je 0x22e02f
22e024: mov rcx, rax
22e027: call 0x227b10
22e02c: mov rbx, rax
22e02f: xor edx, edx
22e031: mov word ptr [rbx + 0x214], r14w
22e039: mov rcx, rbx
22e03c: lea r8d, [rdx + 0x41]
22e040: call 0x235d80
22e045: jmp 0x22da06
22e04a: mov ecx, 0x3b8
22e04f: call 0x4f7a88
22e054: test rax, rax
22e057: je 0x22e064
22e059: mov rcx, rax
22e05c: call 0x227b10
22e061: mov rbx, rax
22e064: xor edx, edx
22e066: mov word ptr [rbx + 0x214], r14w
22e06e: mov rcx, rbx
22e071: lea r8d, [rdx + 0x45]
22e075: call 0x235d80
22e07a: jmp 0x22da06
22e07f: mov ecx, 0x328
22e084: call 0x4f7a88
22e089: mov rbx, rax
22e08c: test rax, rax
22e08f: je 0x22e0e1
22e091: lea rdx, [rip + 0x3bd715] ; b''
22e098: lea rcx, [rbp - 0x48]
22e09c: call 0x3fd6b0
22e0a1: lea rdx, [rip + 0x36b190] ; b'FlmStrk'
22e0a8: lea rcx, [rbp - 0x50]
22e0ac: call 0x3fd6b0
22e0b1: movzx ecx, byte ptr [rip + 0x37069c] ; b'\x0f<\x05\x18\xe0\xa5\x01'
22e0b8: lea r8, [rbp - 0x48]
22e0bc: add cx, cx
22e0bf: lea rdx, [rbp - 0x50]
22e0c3: mov word ptr [rsp + 0x28], cx
22e0c8: mov r9b, 0xff
22e0cb: mov rcx, rbx
22e0ce: mov dword ptr [rsp + 0x20], edi
22e0d2: call 0x227cd0
22e0d7: mov rbx, rax
22e0da: mov edi, 0x180
22e0df: jmp 0x22e0e3
22e0e1: xor ebx, ebx
22e0e3: bt edi, 8
22e0e7: jae 0x22e0f6
22e0e9: btr edi, 8
22e0ed: lea rcx, [rbp - 0x50]
22e0f1: call 0x3fd740
22e0f6: test dil, dil
22e0f9: jns 0x22da06
22e0ff: lea rcx, [rbp - 0x48]
22e103: call 0x3fd740
22e108: jmp 0x22da06
22e10d: mov ecx, 0x328
22e112: call 0x4f7a88
22e117: mov rbx, rax
22e11a: test rax, rax
22e11d: je 0x22e170
22e11f: lea rdx, [rip + 0x3bd687] ; b''
22e126: lea rcx, [rbp - 0x38]
22e12a: call 0x3fd6b0
22e12f: lea rdx, [rip + 0x36b10a] ; b'HLYMITE'
22e136: lea rcx, [rbp - 0x40]
22e13a: call 0x3fd6b0
22e13f: movzx ecx, byte ptr [rip + 0x37060e] ; b'\x0f<\x05\x18\xe0\xa5\x01'
22e146: lea r8, [rbp - 0x38]
22e14a: add cx, cx
22e14d: lea rdx, [rbp - 0x40]
22e151: mov word ptr [rsp + 0x28], cx
22e156: mov r9b, 0xff
22e159: mov rcx, rbx
22e15c: mov dword ptr [rsp + 0x20], r14d
22e161: call 0x227cd0
22e166: mov rbx, rax
22e169: mov edi, 0x600
22e16e: jmp 0x22e172
22e170: xor ebx, ebx
22e172: bt edi, 0xa
22e176: jae 0x22e185
22e178: btr edi, 0xa
22e17c: lea rcx, [rbp - 0x40]
22e180: call 0x3fd740
22e185: bt edi, 9
22e189: jae 0x22da06
22e18f: lea rcx, [rbp - 0x38]
22e193: call 0x3fd740
22e198: jmp 0x22da06
22e19d: lea rdx, [rip + 0x36b0a4] ; b'SHAir'
22e1a4: lea rcx, [rsp + 0x60]
22e1a9: call 0x3fd810
22e1ae: lea rdx, [rip + 0x36b09b] ; b'SHAir7'
22e1b5: lea rcx, [rsp + 0x50]
22e1ba: call 0x3fd810
22e1bf: lea rdx, [rip + 0x3bd5e7] ; b''
22e1c6: lea rcx, [rsp + 0x58]
22e1cb: call 0x3fd810
22e1d0: mov ecx, 0x418
22e1d5: call 0x4f7a88
22e1da: test rax, rax
22e1dd: je 0x22da06
22e1e3: mov byte ptr [rsp + 0x28], bl
22e1e7: lea r9, [rsp + 0x50]
22e1ec: lea r8, [rsp + 0x58]
22e1f1: mov dword ptr [rsp + 0x20], 8
22e1f9: lea rdx, [rsp + 0x60]
22e1fe: mov rcx, rax
22e201: call 0x227df0
22e206: mov rbx, rax
22e209: jmp 0x22da06
22e20e: mov ecx, 0x3e0
22e213: call 0x4f7a88
22e218: mov rbx, rax
22e21b: test rax, rax
22e21e: je 0x22e277
22e220: lea rdx, [rip + 0x36e77d] ; b'ACOWG1'
22e227: lea rcx, [rbp - 8]
22e22b: call 0x3ff7c0
22e230: mov rcx, rbx
22e233: mov rdx, qword ptr [rax]
22e236: call 0x227600
22e23b: mov dword ptr [rsp + 0x40], 0xffffffff
22e243: lea rax, [rip + 0x36d9fe] ; b'\xe0\x82"@\x01'
22e24a: mov byte ptr [rsp + 0x38], dil
22e24f: lea rcx, [rbx + 0x3c8]
22e256: mov byte ptr [rsp + 0x30], dil
22e25b: xor r9d, r9d
22e25e: mov byte ptr [rsp + 0x28], dil
22e263: xor r8d, r8d
22e266: xor edx, edx
22e268: mov byte ptr [rsp + 0x20], dil
22e26d: mov qword ptr [rbx], rax
22e270: call 0x11ba20
22e275: jmp 0x22e279
22e277: xor ebx, ebx
22e279: lea rcx, [rbx + 0x140]
22e280: mov word ptr [rbx + 0x214], r14w
22e288: lea r8, [rip + 0x36e721] ; b'AMB_E42A'
22e28f: lea rdx, [rbp - 0x20]
22e293: call 0x3ff960
22e298: lea rcx, [rbx + 0x14c]
22e29f: lea r8, [rip + 0x36e70a] ; b'AMB_E42A'
22e2a6: lea rdx, [rbp - 0x18]
22e2aa: call 0x3ff960
22e2af: movzx eax, word ptr [rbx + 0x64]
22e2b3: add ax, ax
22e2b6: mov byte ptr [rbx + 0x158], r14b
22e2bd: mov word ptr [rbx + 0x64], ax
22e2c1: mov dword ptr [rbx + 0x3b8], edi
22e2c7: mov dword ptr [rbx + 0x3bc], 0xa
22e2d1: jmp 0x22e8ec
22e2d6: mov ecx, 0x3c8
22e2db: call 0x4f7a88
22e2e0: mov rbx, rax
22e2e3: test rax, rax
22e2e6: je 0x22e3b2
22e2ec: lea rdx, [rip + 0x36e6cd] ; b'spscoric'
22e2f3: lea rcx, [rbp]
22e2f7: call 0x3ff7c0
22e2fc: mov rcx, rbx
22e2ff: mov rdx, qword ptr [rax]
22e302: call 0x227600
22e307: mov rcx, qword ptr [rbx + 0x1b8]
22e30e: lea rax, [rip + 0x36d08b] ; b'\xc0\x83"@\x01'
22e315: xor edx, edx
22e317: mov qword ptr [rbx], rax
22e31a: call 0x411610
22e31f: mov eax, 5
22e324: mov qword ptr [rbx + 0x1f8], rdi
22e32b: lea rcx, [rbx + 0x140]
22e332: mov word ptr [rbx + 0x214], ax
22e339: lea r8, [rip + 0x3bd46d] ; b''
22e340: mov dword ptr [rbx + 0x210], edi
22e346: lea rdx, [rbp - 8]
22e34a: call 0x3ff960
22e34f: mov rcx, qword ptr [rbx + 0x1b8]
22e356: lea r9, [rbp - 0x20]
22e35a: xor r8d, r8d
22e35d: xor edx, edx
22e35f: call 0x4119e0
22e364: movsx ecx, word ptr [rbp - 0x1c]
22e368: mov eax, 0x55555556
22e36d: add ecx, ecx
22e36f: mov dword ptr [rbx + 0x70], 0xffffffff
22e376: imul ecx
22e378: lea rcx, [rbx + 0x178]
22e37f: mov eax, edx
22e381: shr eax, 0x1f
22e384: add edx, eax
22e386: mov word ptr [rbx + 0x64], dx
22e38a: lea rdx, [rip + 0x3bd41c] ; b''
22e391: call 0x3fd810
22e396: mov dword ptr [rbx + 0x180], 0xffffffff
22e3a0: mov word ptr [rbx + 0x3b8], 0x1e
22e3a9: mov byte ptr [rbx + 0x3c0], r14b
22e3b0: jmp 0x22e3b4
22e3b2: xor ebx, ebx
22e3b4: mov byte ptr [rbx + 0x158], r14b
22e3bb: lea r8, [rip + 0x36e496] ; b'TRA_08'
22e3c2: lea rdx, [rbp - 8]
22e3c6: jmp 0x22c31b
22e3cb: mov ecx, 0x328
22e3d0: call 0x4f7a88
22e3d5: mov rbx, rax
22e3d8: test rax, rax
22e3db: je 0x22e42e
22e3dd: lea rdx, [rip + 0x3bd3c9] ; b''
22e3e4: lea rcx, [rbp - 0x28]
22e3e8: call 0x3fd6b0
22e3ed: lea rdx, [rip + 0x36ae4c] ; b'HLYMITE'
22e3f4: lea rcx, [rbp - 0x30]
22e3f8: call 0x3fd6b0
22e3fd: movzx ecx, byte ptr [rip + 0x370350] ; b'\x0f<\x05\x18\xe0\xa5\x01'
22e404: lea r8, [rbp - 0x28]
22e408: add cx, cx
22e40b: lea rdx, [rbp - 0x30]
22e40f: mov word ptr [rsp + 0x28], cx
22e414: mov r9b, 0xff
22e417: mov rcx, rbx
22e41a: mov dword ptr [rsp + 0x20], r14d
22e41f: call 0x227cd0
22e424: mov rbx, rax
22e427: mov edi, 0x1800
22e42c: jmp 0x22e430
22e42e: xor ebx, ebx
22e430: bt edi, 0xc
22e434: jae 0x22e443
22e436: btr edi, 0xc
22e43a: lea rcx, [rbp - 0x30]
22e43e: call 0x3fd740
22e443: bt edi, 0xb
22e447: jae 0x22e452
22e449: lea rcx, [rbp - 0x28]
22e44d: call 0x3fd740
22e452: lea rcx, [rbx + 0x1c0]
22e459: mov edx, 0xff
22e45e: call 0x412690
22e463: lea r8, [rip + 0x36e566] ; b'EFF_M10'
22e46a: jmp 0x22e8c5
22e46f: lea rdx, [rip + 0x36e562] ; b'SHAREA'
22e476: lea rcx, [rsp + 0x60]
22e47b: call 0x3fd810
22e480: lea rdx, [rip + 0x3bd326] ; b''
22e487: lea rcx, [rsp + 0x50]
22e48c: call 0x3fd810
22e491: lea rdx, [rip + 0x3bd315] ; b''
22e498: lea rcx, [rsp + 0x58]
22e49d: call 0x3fd810
22e4a2: mov ecx, 0x418
22e4a7: call 0x4f7a88
22e4ac: test rax, rax
22e4af: je 0x22e8be
22e4b5: mov byte ptr [rsp + 0x28], bl
22e4b9: lea r9, [rsp + 0x50]
22e4be: lea r8, [rsp + 0x58]
22e4c3: mov dword ptr [rsp + 0x20], 8
22e4cb: lea rdx, [rsp + 0x60]
22e4d0: mov rcx, rax
22e4d3: call 0x227df0
22e4d8: mov rbx, rax
22e4db: jmp 0x22e8be
22e4e0: lea rdx, [rip + 0x36e4f1] ; b'SHAREA'
22e4e7: lea rcx, [rsp + 0x60]
22e4ec: call 0x3fd810
22e4f1: lea rdx, [rip + 0x36e4e8] ; b'SHAREA1'
22e4f8: lea rcx, [rsp + 0x50]
22e4fd: call 0x3fd810
22e502: lea rdx, [rip + 0x3bd2a4] ; b''
22e509: lea rcx, [rsp + 0x58]
22e50e: call 0x3fd810
22e513: mov ecx, 0x418
22e518: call 0x4f7a88
22e51d: test rax, rax
22e520: je 0x22e8be
22e526: mov byte ptr [rsp + 0x28], bl
22e52a: lea r9, [rsp + 0x50]
22e52f: lea r8, [rsp + 0x58]
22e534: mov dword ptr [rsp + 0x20], 8
22e53c: lea rdx, [rsp + 0x60]
22e541: mov rcx, rax
22e544: call 0x227df0
22e549: mov rbx, rax
22e54c: jmp 0x22e8be
22e551: lea rdx, [rip + 0x36e480] ; b'SHAREA'
22e558: lea rcx, [rsp + 0x60]
22e55d: call 0x3fd810
22e562: lea rdx, [rip + 0x36e47f] ; b'SHAREA3'
22e569: lea rcx, [rsp + 0x50]
22e56e: call 0x3fd810
22e573: lea rdx, [rip + 0x3bd233] ; b''
22e57a: lea rcx, [rsp + 0x58]
22e57f: call 0x3fd810
22e584: mov ecx, 0x418
22e589: call 0x4f7a88
22e58e: test rax, rax
22e591: je 0x22e8be
22e597: mov byte ptr [rsp + 0x28], bl
22e59b: lea r9, [rsp + 0x50]
22e5a0: lea r8, [rsp + 0x58]
22e5a5: mov dword ptr [rsp + 0x20], 8
22e5ad: lea rdx, [rsp + 0x60]
22e5b2: mov rcx, rax
22e5b5: call 0x227df0
22e5ba: mov rbx, rax
22e5bd: jmp 0x22e8be
22e5c2: lea rdx, [rip + 0x36e40f] ; b'SHAREA'
22e5c9: lea rcx, [rsp + 0x60]
22e5ce: call 0x3fd810
22e5d3: lea rdx, [rip + 0x36e416] ; b'SHAREA4'
22e5da: lea rcx, [rsp + 0x50]
22e5df: call 0x3fd810
22e5e4: lea rdx, [rip + 0x3bd1c2] ; b''
22e5eb: lea rcx, [rsp + 0x58]
22e5f0: call 0x3fd810
22e5f5: mov ecx, 0x418
22e5fa: call 0x4f7a88
22e5ff: test rax, rax
22e602: je 0x22e8be
22e608: mov byte ptr [rsp + 0x28], bl
22e60c: lea r9, [rsp + 0x50]
22e611: lea r8, [rsp + 0x58]
22e616: mov dword ptr [rsp + 0x20], 8
22e61e: lea rdx, [rsp + 0x60]
22e623: mov rcx, rax
22e626: call 0x227df0
22e62b: mov rbx, rax
22e62e: jmp 0x22e8be
22e633: lea rdx, [rip + 0x36e39e] ; b'SHAREA'
22e63a: lea rcx, [rsp + 0x60]
22e63f: call 0x3fd810
22e644: lea rdx, [rip + 0x36e3ad] ; b'SHAREA5'
22e64b: lea rcx, [rsp + 0x50]
22e650: call 0x3fd810
22e655: lea rdx, [rip + 0x3bd151] ; b''
22e65c: lea rcx, [rsp + 0x58]
22e661: call 0x3fd810
22e666: mov ecx, 0x418
22e66b: call 0x4f7a88
22e670: test rax, rax
22e673: je 0x22e8be
22e679: mov byte ptr [rsp + 0x28], bl
22e67d: lea r9, [rsp + 0x50]
22e682: lea r8, [rsp + 0x58]
22e687: mov dword ptr [rsp + 0x20], 8
22e68f: lea rdx, [rsp + 0x60]
22e694: mov rcx, rax
22e697: call 0x227df0
22e69c: mov rbx, rax
22e69f: jmp 0x22e8be
22e6a4: lea rdx, [rip + 0x36e32d] ; b'SHAREA'
22e6ab: lea rcx, [rsp + 0x60]
22e6b0: call 0x3fd810
22e6b5: lea rdx, [rip + 0x36e344] ; b'SHAREA6'
22e6bc: lea rcx, [rsp + 0x50]
22e6c1: call 0x3fd810
22e6c6: lea rdx, [rip + 0x3bd0e0] ; b''
22e6cd: lea rcx, [rsp + 0x58]
22e6d2: call 0x3fd810
22e6d7: mov ecx, 0x418
22e6dc: call 0x4f7a88
22e6e1: test rax, rax
22e6e4: je 0x22e8be
22e6ea: mov byte ptr [rsp + 0x28], bl
22e6ee: lea r9, [rsp + 0x50]
22e6f3: lea r8, [rsp + 0x58]
22e6f8: mov dword ptr [rsp + 0x20], 8
22e700: lea rdx, [rsp + 0x60]
22e705: mov rcx, rax
22e708: call 0x227df0
22e70d: mov rbx, rax
22e710: jmp 0x22e8be
22e715: lea rdx, [rip + 0x36e2bc] ; b'SHAREA'
22e71c: lea rcx, [rsp + 0x60]
22e721: call 0x3fd810
22e726: lea rdx, [rip + 0x36e2db] ; b'SHAREA2'
22e72d: lea rcx, [rsp + 0x50]
22e732: call 0x3fd810
22e737: lea rdx, [rip + 0x3bd06f] ; b''
22e73e: lea rcx, [rsp + 0x58]
22e743: call 0x3fd810
22e748: mov ecx, 0x418
22e74d: call 0x4f7a88
22e752: test rax, rax
22e755: je 0x22e8be
22e75b: mov byte ptr [rsp + 0x28], bl
22e75f: lea r9, [rsp + 0x50]
22e764: lea r8, [rsp + 0x58]
22e769: mov dword ptr [rsp + 0x20], 8
22e771: lea rdx, [rsp + 0x60]
22e776: mov rcx, rax
22e779: call 0x227df0
22e77e: mov rbx, rax
22e781: jmp 0x22e8be
22e786: lea rdx, [rip + 0x36aacb] ; b'SPFDEATH'
22e78d: lea rcx, [rsp + 0x60]
22e792: call 0x3fd810
22e797: lea rdx, [rip + 0x3bd00f] ; b''
22e79e: lea rcx, [rsp + 0x50]
22e7a3: call 0x3fd810
22e7a8: lea rdx, [rip + 0x36aab9] ; b'EFF_P17'
22e7af: jmp 0x22e498
22e7b4: mov ecx, 0x328
22e7b9: call 0x4f7a88
22e7be: mov rbx, rax
22e7c1: test rax, rax
22e7c4: je 0x22e817
22e7c6: lea rdx, [rip + 0x36e243] ; b'EFF_P78'
22e7cd: lea rcx, [rbp - 0x10]
22e7d1: call 0x3fd6b0
22e7d6: lea rdx, [rip + 0x36e23b] ; b'SPHOLYMT'
22e7dd: lea rcx, [rbp + 8]
22e7e1: call 0x3fd6b0
22e7e6: movzx ecx, byte ptr [rip + 0x36ff67] ; b'\x0f<\x05\x18\xe0\xa5\x01'
22e7ed: lea r8, [rbp - 0x10]
22e7f1: add cx, cx
22e7f4: lea rdx, [rbp + 8]
22e7f8: mov word ptr [rsp + 0x28], cx
22e7fd: mov r9b, 0xff
22e800: mov rcx, rbx
22e803: mov dword ptr [rsp + 0x20], r14d
22e808: call 0x227cd0
22e80d: mov rbx, rax
22e810: mov edi, 0x6000
22e815: jmp 0x22e819
22e817: xor ebx, ebx
22e819: bt edi, 0xe
22e81d: jae 0x22e82c
22e81f: btr edi, 0xe
22e823: lea rcx, [rbp + 8]
22e827: call 0x3fd740
22e82c: bt edi, 0xd
22e830: jae 0x22e8be
22e836: lea rcx, [rbp - 0x10]
22e83a: jmp 0x22e8b9
22e83c: mov ecx, 0x328
22e841: call 0x4f7a88
22e846: mov rbx, rax
22e849: test rax, rax
22e84c: je 0x22e89a
22e84e: lea rdx, [rip + 0x3bcf58] ; b''
22e855: lea rcx, [rbp - 0x20]
22e859: call 0x3fd6b0
22e85e: lea rdx, [rip + 0x36e1c3] ; b'SPgenHLa'
22e865: lea rcx, [rbp - 0x18]
22e869: call 0x3fd6b0
22e86e: mov eax, 0x1d
22e873: lea r8, [rbp - 0x20]
22e877: mov word ptr [rsp + 0x28], ax
22e87c: lea rdx, [rbp - 0x18]
22e880: mov r9b, 0xff
22e883: mov dword ptr [rsp + 0x20], r14d
22e888: mov rcx, rbx
22e88b: call 0x227cd0
22e890: mov rbx, rax
22e893: mov edi, 0x18000
22e898: jmp 0x22e89c
22e89a: xor ebx, ebx
22e89c: bt edi, 0x10
22e8a0: jae 0x22e8af
22e8a2: btr edi, 0x10
22e8a6: lea rcx, [rbp - 0x18]
22e8aa: call 0x3fd740
22e8af: bt edi, 0xf
22e8b3: jae 0x22e8be
22e8b5: lea rcx, [rbp - 0x20]
22e8b9: call 0x3fd740
22e8be: lea r8, [rip + 0x3bcee8] ; b''
22e8c5: lea rdx, [rbp]
22e8c9: lea rcx, [rbx + 0x140]
22e8d0: call 0x3ff960
22e8d5: lea rdx, [rbp - 8]
22e8d9: lea r8, [rip + 0x3bcecd] ; b''
22e8e0: lea rcx, [rbx + 0x14c]
22e8e7: call 0x3ff960
22e8ec: test rbx, rbx
22e8ef: jne 0x22ed7f
22e8f5: mov rax, qword ptr [rip + 0x438c4c] ; b''
22e8fc: mov edx, r12d
22e8ff: mov rcx, qword ptr [rax + 0x1090]
22e906: add rcx, 0x1810
22e90d: call 0x11b480
22e912: mov rdi, rax
22e915: test rax, rax
22e918: je 0x22e94d
22e91a: mov ecx, 0x3b8
22e91f: call 0x4f7a88
22e924: test rax, rax
22e927: je 0x22e936
22e929: mov rcx, rax
22e92c: call 0x227a40
22e931: mov rbx, rax
22e934: jmp 0x22e938
22e936: xor ebx, ebx
22e938: lea rdx, [rdi + 8]
22e93c: lea rcx, [rbx + 0x178]
22e943: call 0x3fd770
22e948: jmp 0x22ed7f
22e94d: mov rax, qword ptr [rip + 0x438bf4] ; b''
22e954: mov edx, r12d
22e957: mov rcx, qword ptr [rax + 0x1090]
22e95e: add rcx, 0x1880
22e965: call 0x11b480
22e96a: test rax, rax
22e96d: je 0x22ed47
22e973: lea r12, [rax + 8]
22e977: mov rdx, r12
22e97a: lea rcx, [rbp]
22e97e: call 0x3ff710
22e983: lea rcx, [rbp + 0x10]
22e987: mov rdx, qword ptr [rax]
22e98a: call 0x227930
22e98f: mov rcx, qword ptr [rbp + 0x10]
22e993: test rcx, rcx
22e996: je 0x22ed47
22e99c: call 0x3f6d50
22e9a1: test rax, rax
22e9a4: je 0x22ed1e
22e9aa: mov rcx, qword ptr [rbp + 0x10]
22e9ae: mov eax, dword ptr [rcx + 0x48]
22e9b1: cmp eax, 8
22e9b4: jbe 0x22ed1e
22e9ba: add eax, -8
22e9bd: je 0x22ed1e
22e9c3: call 0x3f6d50
22e9c8: mov r15, rax
22e9cb: add r15, 8
22e9cf: je 0x22ed1e
22e9d5: test dword ptr [r15 + 0x24], 0x100000
22e9dd: je 0x22ea9b
22e9e3: mov rax, qword ptr [rsi]
22e9e6: mov rcx, rsi
22e9e9: call qword ptr [rax + 8]
22e9ec: cmp al, byte ptr [rip + 0x36ad2d] ; b'10AQaq`p'
22e9f2: jne 0x22ea9b
22e9f8: movzx eax, byte ptr [rsi + 0x586]
22e9ff: lea rcx, [rip - 0x22ea06]
22ea06: mov r13d, dword ptr [rcx + rax*4 + 0x5c0710]
22ea0e: mov ecx, 0x30
22ea13: call 0x4f7a88
22ea18: mov r14, rax
22ea1b: test rax, rax
22ea1e: je 0x22ea7a
22ea20: mov edi, dword ptr [rsi + 0x48]
22ea23: mov rcx, qword ptr [rsp + 0x68]
22ea28: mov esi, dword ptr [r15 + 0x28]
22ea2c: call 0x3579b0
22ea31: lea rcx, [rip + 0x360740] ; b'\x90\xde\x14@\x01'
22ea38: mov dword ptr [r14 + 0x14], esi
22ea3c: mov rsi, qword ptr [rsp + 0x68]
22ea41: mov qword ptr [r14], rcx
22ea44: mov dword ptr [r14 + 0xc], edi
22ea48: mov dword ptr [r14 + 8], edi
22ea4c: mov dword ptr [r14 + 0x10], eax
22ea50: mov dword ptr [r14 + 0x18], r13d
22ea54: mov dword ptr [r14 + 0x1c], 0xbed7d7
22ea5c: mov dword ptr [r14 + 0x20], 0xffffffff
22ea64: mov byte ptr [r14 + 0x24], 0
22ea69: mov dword ptr [r14 + 0x28], 0
22ea71: mov word ptr [r14 + 0x2c], 0x100
22ea78: jmp 0x22ea7d
22ea7a: xor r14d, r14d
22ea7d: mov rcx, qword ptr [rip + 0x438ac4] ; b''
22ea84: xor r8d, r8d
22ea87: add rcx, 0x1768
22ea8e: mov rdx, r14
22ea91: call 0x204ec0
22ea96: movzx r13d, word ptr [rbp - 0x80]
22ea9b: movzx ecx, word ptr [r15]
22ea9f: sub ecx, 1
22eaa2: je 0x22ecf1
22eaa8: sub ecx, 1
22eaab: je 0x22eafd
22eaad: cmp ecx, 1
22eab0: jne 0x22ed1e
22eab6: mov ecx, 0x4a8
22eabb: call 0x4f7a88
22eac0: mov rbx, rax
22eac3: test rax, rax
22eac6: je 0x22eaf3
22eac8: mov rdx, r12
22eacb: lea rcx, [rsp + 0x68]
22ead0: call 0x3ff710
22ead5: mov r8, rsi
22ead8: mov rdx, r15
22eadb: mov rcx, rbx
22eade: mov r9, qword ptr [rax]
22eae1: call 0x226b80
22eae6: mov rbx, rax
22eae9: mov eax, 3
22eaee: jmp 0x22ed17
22eaf3: xor ebx, ebx
22eaf5: lea eax, [rbx + 3]
22eaf8: jmp 0x22ed17
22eafd: mov eax, dword ptr [r15 + 0x24]
22eb01: test al, al
22eb03: jns 0x22eb8b
22eb09: mov ecx, 0x3b8
22eb0e: call 0x4f7a88
22eb13: mov rbx, rax
22eb16: test rax, rax
22eb19: je 0x22ece8
22eb1f: mov rdx, r15
22eb22: mov rcx, rax
22eb25: call 0x2270e0
22eb2a: test dword ptr [rbx + 0x188], 0x20000
22eb34: lea rax, [rip + 0x36dbdd] ; b'\xd0\x81"@\x01'
22eb3b: mov qword ptr [rbx], rax
22eb3e: je 0x22eb61
22eb40: movzx ecx, byte ptr [rip + 0x36fc0d] ; b'\x0f<\x05\x18\xe0\xa5\x01'
22eb47: movzx eax, cx
22eb4a: add ax, ax
22eb4d: add cx, ax
22eb50: mov eax, 2
22eb55: mov word ptr [rbx + 0x184], cx
22eb5c: jmp 0x22ed17
22eb61: mov rcx, qword ptr [rbx + 0x1b8]
22eb68: movzx edx, word ptr [rcx + 0x11a]
22eb6f: call 0x411cc0
22eb74: movzx ecx, al
22eb77: mov eax, 2
22eb7c: dec cx
22eb7f: mov word ptr [rbx + 0x184], cx
22eb86: jmp 0x22ed17
22eb8b: bt eax, 0xa
22eb8f: jae 0x22ec4c
22eb95: mov ecx, 0x3f0
22eb9a: call 0x4f7a88
22eb9f: mov rbx, rax
22eba2: test rax, rax
22eba5: je 0x22ece8
22ebab: mov rdx, r15
22ebae: mov rcx, rax
22ebb1: call 0x2270e0
22ebb6: lea rax, [rip + 0x36d2fb] ; b'0\x83"@\x01'
22ebbd: mov edx, 0xa
22ebc2: lea rcx, [rbx + 0x3b8]
22ebc9: mov qword ptr [rbx], rax
22ebcc: call 0x4073a0
22ebd1: cmp qword ptr [rsp + 0x68], 0
22ebd7: lea rax, [rip + 0x35e17a] ; b'\x90n\x11@\x01'
22ebde: mov qword ptr [rbx + 0x3b8], rax
22ebe5: jne 0x22ebfa
22ebe7: mov eax, 1
22ebec: mov word ptr [rbx + 0x4c], ax
22ebf0: mov eax, 2
22ebf5: jmp 0x22ed17
22ebfa: test r13w, r13w
22ebfe: je 0x22ecea
22ec04: mov r14d, 0xffff
22ec0a: nop word ptr [rax + rax]
22ec10: xor edx, edx
22ec12: movzx ecx, r13w
22ec16: call 0x22bf00
22ec1b: mov rdx, rax
22ec1e: lea rcx, [rbx + 0x3b8]
22ec25: mov rdi, rax
22ec28: add r13w, r14w
22ec2c: call 0x4075c0
22ec31: cmp word ptr [rdi + 0x4c], 0
22ec36: je 0x22ecea
22ec3c: test r13w, r13w
22ec40: jne 0x22ec10
22ec42: mov eax, 2
22ec47: jmp 0x22ed17
22ec4c: bt eax, 0xe
22ec50: jae 0x22ecc4
22ec52: mov ecx, 0x4d8
22ec57: call 0x4f7a88
22ec5c: mov rbx, rax
22ec5f: test rax, rax
22ec62: je 0x22ece8
22ec68: mov rdx, r15
22ec6b: mov rcx, rax
22ec6e: call 0x2270e0
22ec73: lea rax, [rip + 0x36c85e] ; b'\x80\x83"@\x01'
22ec7a: mov dword ptr [rbx + 0x4cc], 0x3c
22ec84: mov qword ptr [rbx], rax
22ec87: xor edi, edi
22ec89: mov eax, 3
22ec8e: mov dword ptr [rbx + 0x4c4], edi
22ec94: mov dword ptr [rbx + 0x4c8], eax
22ec9a: call 0x232aa0
22ec9f: mov eax, 0x6e
22eca4: mov dword ptr [rbx + 0x70], 0xffffffff
22ecab: mov word ptr [rbx + 0x184], ax
22ecb2: lea eax, [rdi + 2]
22ecb5: mov byte ptr [rbx + 0x3b8], dil
22ecbc: mov dword ptr [rbx + 0x4c0], edi
22ecc2: jmp 0x22ed17
22ecc4: mov ecx, 0x3b8
22ecc9: call 0x4f7a88
22ecce: test rax, rax
22ecd1: je 0x22ece8
22ecd3: mov rdx, r15
22ecd6: mov rcx, rax
22ecd9: call 0x2270e0
22ecde: mov rbx, rax
22ece1: mov eax, 2
22ece6: jmp 0x22ed17
22ece8: xor ebx, ebx
22ecea: mov eax, 2
22ecef: jmp 0x22ed17
22ecf1: mov ecx, 0x1b8
22ecf6: call 0x4f7a88
22ecfb: test rax, rax
22ecfe: je 0x22ed10
22ed00: mov rdx, r15
22ed03: mov rcx, rax
22ed06: call 0x226630
22ed0b: mov rbx, rax
22ed0e: jmp 0x22ed12
22ed10: xor ebx, ebx
22ed12: mov eax, 1
22ed17: mov word ptr [rbx + 0xca], ax
22ed1e: cmp qword ptr [rbp + 0x10], 0
22ed23: je 0x22ed42
22ed25: lea rdx, [rip + 0x3bca81] ; b''
22ed2c: lea rcx, [rbp + 0x18]
22ed30: call 0x3ffb60
22ed35: test eax, eax
22ed37: je 0x22ed42
22ed39: mov rcx, qword ptr [rbp + 0x10]
22ed3d: call 0x1e1e0
22ed42: test rbx, rbx
22ed45: jne 0x22ed7f
22ed47: mov ecx, 0x1b8
22ed4c: call 0x4f7a88
22ed51: mov rbx, rax
22ed54: test rax, rax
22ed57: je 0x22ed7d
22ed59: xor edx, edx
22ed5b: mov r8d, 0x1b8
22ed61: mov rcx, rax
22ed64: call 0x4fab70
22ed69: mov rcx, rbx
22ed6c: call 0x226910
22ed71: lea rax, [rip + 0x36d278] ; b'\xf0\x80"@\x01'
22ed78: mov qword ptr [rbx], rax
22ed7b: jmp 0x22ed7f
22ed7d: xor ebx, ebx
22ed7f: mov eax, dword ptr [rbp - 0x7c]
22ed82: lea rcx, [rbp + 0x28]
22ed86: dec ax
22ed89: mov word ptr [rbx + 0x60], ax
22ed8d: call 0x3fd740
22ed92: lea rcx, [rsp + 0x50]
22ed97: call 0x3fd740
22ed9c: lea rcx, [rsp + 0x58]
22eda1: call 0x3fd740
22eda6: lea rcx, [rsp + 0x60]
22edab: call 0x3fd740
22edb0: mov rax, rbx
22edb3: mov rcx, qword ptr [rbp + 0x58]
22edb7: xor rcx, rsp
22edba: call 0x4f77a0
22edbf: mov rbx, qword ptr [rsp + 0x1b0]
22edc7: add rsp, 0x160
22edce: pop r15
22edd0: pop r14
22edd2: pop r13
22edd4: pop r12
22edd6: pop rdi
22edd7: pop rsi
22edd8: pop rbp
22edd9: ret 
