1e8a20: mov qword ptr [rsp + 0x10], rbx
1e8a25: push rbp
1e8a26: push rsi
1e8a27: push rdi
1e8a28: push r12
1e8a2a: push r13
1e8a2c: push r14
1e8a2e: push r15
1e8a30: mov rbp, rsp
1e8a33: sub rsp, 0x40
1e8a37: mov rax, qword ptr [rip + 0x47bf9a] ; b'2\xa2\xdf-\x99+'
1e8a3e: xor rax, rsp
1e8a41: mov qword ptr [rbp - 0x10], rax
1e8a45: mov rbx, r9
1e8a48: movzx esi, dl
1e8a4b: movzx edi, r8w
1e8a4f: mov r14, rcx
1e8a52: call 0x1eca50
1e8a57: lea rax, [rip + 0x3b0a72] ; b'\xa0\x97\x1e@\x01'
1e8a5e: lea r13, [r14 + 0x90]
1e8a65: mov qword ptr [r14], rax
1e8a68: mov rcx, r13
1e8a6b: call 0x410f70
1e8a70: movzx edx, word ptr [rip + 0x3d7c05] ; b'\x01'
1e8a77: lea rcx, [r14 + 0x1c8]
1e8a7e: call 0x421010
1e8a83: lea r12, [r14 + 0x230]
1e8a8a: mov rcx, r12
1e8a8d: call 0x40d580
1e8a92: mov rax, qword ptr [rip + 0x474077] ; b'$\xcbe@\x01'
1e8a99: lea r15, [r14 + 0x250]
1e8aa0: lea rcx, [r14 + 0x290]
1e8aa7: mov qword ptr [r15], rax
1e8aaa: call 0x410d80
1e8aaf: lea rcx, [r14 + 0x3b0]
1e8ab6: call 0x3ff870
1e8abb: lea rcx, [r14 + 0x3b8]
1e8ac2: call 0x3ff870
1e8ac7: movzx r8d, byte ptr [rbp + 0x68]
1e8acc: xor ecx, ecx
1e8ace: mov qword ptr [r14 + 0x258], rcx
1e8ad5: mov eax, 1
1e8ada: mov dword ptr [r14 + 0x264], eax
1e8ae1: mov qword ptr [r14 + 0x268], rax
1e8ae8: mov dword ptr [r14 + 0x288], ecx
1e8aef: mov qword ptr [r14 + 0x270], rcx
1e8af6: mov dword ptr [r14 + 0x260], ecx
1e8afd: movsx ecx, word ptr [rbp + 0x60]
1e8b01: mov byte ptr [r14 + 8], 0x70
1e8b06: mov eax, dword ptr [rbx]
1e8b08: mov dword ptr [r14 + 0x84], eax
1e8b0f: movzx eax, word ptr [rbx + 4]
1e8b13: mov word ptr [r14 + 0x88], ax
1e8b1b: movzx eax, byte ptr [rbx + 6]
1e8b1f: mov byte ptr [r14 + 0x8a], al
1e8b26: lea eax, [rcx - 1]
1e8b29: cdq 
1e8b2a: mov dword ptr [r14 + 0x1fc], ecx
1e8b31: idiv r8d
1e8b34: mov dword ptr [r14 + 0x200], r8d
1e8b3b: inc al
1e8b3d: mov byte ptr [r14 + 0x204], al
1e8b44: movzx eax, word ptr [rbp + 0x80]
1e8b4b: mov word ptr [r14 + 0x1f8], ax
1e8b53: movzx eax, byte ptr [rbp + 0x70]
1e8b57: mov byte ptr [r14 + 0x205], al
1e8b5e: mov eax, dword ptr [rbp + 0x88]
1e8b64: mov dword ptr [r14 + 0x278], eax
1e8b6b: movzx eax, word ptr [rbp + 0x90]
1e8b72: mov word ptr [r14 + 0x27c], ax
1e8b7a: mov rax, qword ptr [rbp + 0x98]
1e8b81: mov rcx, qword ptr [rax]
1e8b84: mov qword ptr [r14 + 0x280], rcx
1e8b8b: lea rcx, [r14 + 0x1c8]
1e8b92: movzx eax, byte ptr [rip + 0x3b2467] ; b'\x10\x0c\xff\x05@\x01\x01'
1e8b99: lea eax, [rax + rax*2]
1e8b9c: cdq 
1e8b9d: sub eax, edx
1e8b9f: xor edx, edx
1e8ba1: sar eax, 1
1e8ba3: mov word ptr [r14 + 0x8c], ax
1e8bab: mov rax, qword ptr [rip + 0x47e996] ; b''
1e8bb2: movzx r8d, byte ptr [rbx]
1e8bb6: mov r9, qword ptr [rax + 0x1090]
1e8bbd: add r9, 0x63d8
1e8bc4: call 0x4221c0
1e8bc9: mov rax, qword ptr [rip + 0x47e978] ; b''
1e8bd0: lea rcx, [r14 + 0x1c8]
1e8bd7: movzx r8d, byte ptr [rbx + 1]
1e8bdc: mov edx, 1
1e8be1: mov r9, qword ptr [rax + 0x1090]
1e8be8: add r9, 0x63d8
1e8bef: call 0x4221c0
1e8bf4: mov word ptr [r14 + 0x3c0], di
1e8bfc: mov eax, dword ptr [rbp + 0x78]
1e8bff: xor edi, edi
1e8c01: and eax, 0x40
1e8c04: mov dword ptr [r14 + 0x3c4], edi
1e8c0b: mov dword ptr [r14 + 0x3c8], eax
1e8c12: cmp esi, 0xfe
1e8c18: ja 0x1e9623
1e8c1e: lea rdx, [rip - 0x1e8c25]
1e8c25: movzx eax, byte ptr [rdx + rsi + 0x1e969c]
1e8c2d: mov ecx, dword ptr [rdx + rax*4 + 0x1e964c]
1e8c34: add rcx, rdx
1e8c37: jmp rcx
1e8c39: lea rdx, [rip + 0x402b6d] ; b''
1e8c40: mov rcx, r15
1e8c43: call 0x3fd810
1e8c48: mov qword ptr [r14 + 0x264], rdi
1e8c4f: mov dword ptr [r14 + 0x260], edi
1e8c56: mov dword ptr [r14 + 0x80], 0xf010f00
1e8c61: jmp 0x1e9623
1e8c66: lea rdx, [rip + 0x3b0933] ; b'EFF_M21'
1e8c6d: lea rcx, [rbp - 0x20]
1e8c71: call 0x3ff7c0
1e8c76: mov edi, 1
1e8c7b: lea rdx, [rbp - 0x20]
1e8c7f: mov r9d, edi
1e8c82: mov r8d, edi
1e8c85: mov rcx, r12
1e8c88: call 0x40ede0
1e8c8d: lea rdx, [rip + 0x402b19] ; b''
1e8c94: mov rcx, r15
1e8c97: call 0x3fd810
1e8c9c: mov rax, qword ptr [rip + 0x47e8a5] ; b''
1e8ca3: mov rcx, qword ptr [rax + 0x1090]
1e8caa: cmp dword ptr [rcx + 0x7e54], 0
1e8cb1: je 0x1e8cc2
1e8cb3: cmp dword ptr [rcx + 0x7d98], 0
1e8cba: je 0x1e8cc2
1e8cbc: mov eax, edi
1e8cbe: xor esi, esi
1e8cc0: jmp 0x1e8cc6
1e8cc2: xor esi, esi
1e8cc4: mov eax, esi
1e8cc6: lea rcx, [rbp - 0x20]
1e8cca: test eax, eax
1e8ccc: je 0x1e8e90
1e8cd2: lea rdx, [rip + 0x3b08cf] ; b'SPFIREPI'
1e8cd9: mov dword ptr [r14 + 0x80], 0x10001
1e8ce4: call 0x3ff7c0
1e8ce9: mov r9d, edi
1e8cec: lea rdx, [rbp - 0x20]
1e8cf0: mov r8d, edi
1e8cf3: lea rcx, [r14 + 0x198]
1e8cfa: call 0x14d080
1e8cff: mov dword ptr [r14 + 0x260], edi
1e8d06: mov dword ptr [r14 + 0x268], esi
1e8d0d: jmp 0x1e8f91
1e8d12: lea rdx, [rip + 0x3b0887] ; b'EFF_M21'
1e8d19: lea rcx, [rbp - 0x20]
1e8d1d: call 0x3ff7c0
1e8d22: mov edi, 1
1e8d27: lea rdx, [rbp - 0x20]
1e8d2b: mov r9d, edi
1e8d2e: mov r8d, edi
1e8d31: mov rcx, r12
1e8d34: call 0x40ede0
1e8d39: lea rdx, [rip + 0x402a6d] ; b''
1e8d40: mov rcx, r15
1e8d43: call 0x3fd810
1e8d48: mov rax, qword ptr [rip + 0x47e7f9] ; b''
1e8d4f: mov rcx, qword ptr [rax + 0x1090]
1e8d56: cmp dword ptr [rcx + 0x7e54], 0
1e8d5d: je 0x1e8d6e
1e8d5f: cmp dword ptr [rcx + 0x7d98], 0
1e8d66: je 0x1e8d6e
1e8d68: mov eax, edi
1e8d6a: xor esi, esi
1e8d6c: jmp 0x1e8d72
1e8d6e: xor esi, esi
1e8d70: mov eax, esi
1e8d72: lea rcx, [rbp - 0x20]
1e8d76: test eax, eax
1e8d78: je 0x1e8e90
1e8d7e: lea rdx, [rip + 0x3b0823] ; b'SPFIREPI'
1e8d85: mov dword ptr [r14 + 0x80], 0x30003
1e8d90: call 0x3ff7c0
1e8d95: mov r9d, edi
1e8d98: lea rdx, [rbp - 0x20]
1e8d9c: mov r8d, edi
1e8d9f: lea rcx, [r14 + 0x198]
1e8da6: call 0x14d080
1e8dab: lea rdx, [rip + 0x3b080e] ; b'SPFIREPB'
1e8db2: mov dword ptr [r14 + 0x260], edi
1e8db9: lea rcx, [rbp - 0x20]
1e8dbd: mov dword ptr [r14 + 0x268], esi
1e8dc4: mov dword ptr [r14 + 0x288], edi
1e8dcb: call 0x3ff7c0
1e8dd0: mov rax, qword ptr [r14 + 0x398]
1e8dd7: cmp rax, qword ptr [rbp - 0x20]
1e8ddb: je 0x1e8f91
1e8de1: cmp qword ptr [r14 + 0x390], 0
1e8de9: je 0x1e8e0e
1e8deb: lea rdx, [rip + 0x4029bb] ; b''
1e8df2: lea rcx, [r14 + 0x398]
1e8df9: call 0x3ffb60
1e8dfe: test eax, eax
1e8e00: je 0x1e8e0e
1e8e02: mov rcx, qword ptr [r14 + 0x390]
1e8e09: call 0x1e1e0
1e8e0e: lea rdx, [rip + 0x402998] ; b''
1e8e15: lea rcx, [rbp - 0x20]
1e8e19: call 0x3ffa80
1e8e1e: test eax, eax
1e8e20: je 0x1e8e45
1e8e22: lea r8, [rip + 0x402984] ; b''
1e8e29: mov qword ptr [r14 + 0x390], rsi
1e8e30: lea rdx, [rbp - 0x18]
1e8e34: lea rcx, [r14 + 0x398]
1e8e3b: call 0x3ff960
1e8e40: jmp 0x1e8f91
1e8e45: xor r8d, r8d
1e8e48: lea rcx, [rbp - 0x20]
1e8e4c: mov edx, edi
1e8e4e: call 0x403790
1e8e53: lea rdx, [rbp - 0x18]
1e8e57: lea rcx, [r14 + 0x398]
1e8e5e: test rax, rax
1e8e61: jne 0x1e8e7b
1e8e63: lea r8, [rip + 0x402943] ; b''
1e8e6a: mov qword ptr [r14 + 0x390], rsi
1e8e71: call 0x3ff960
1e8e76: jmp 0x1e8f91
1e8e7b: lea r8, [rbp - 0x20]
1e8e7f: mov qword ptr [r14 + 0x390], rax
1e8e86: call 0x3ff880
1e8e8b: jmp 0x1e8f91
1e8e90: lea rdx, [rip + 0x3b071d] ; b'SPBOOM'
1e8e97: mov dword ptr [r14 + 0x80], 0
1e8ea2: call 0x3ff7c0
1e8ea7: mov r9d, edi
1e8eaa: lea rdx, [rbp - 0x20]
1e8eae: mov r8d, edi
1e8eb1: lea rcx, [r14 + 0x198]
1e8eb8: call 0x14d080
1e8ebd: lea rdx, [r14 + 0x1c8]
1e8ec4: mov rcx, r13
1e8ec7: call 0x412390
1e8ecc: jmp 0x1e8f91
1e8ed1: lea rdx, [rip + 0x3b06c8] ; b'EFF_M21'
1e8ed8: lea rcx, [rbp - 0x20]
1e8edc: call 0x3ff7c0
1e8ee1: mov edi, 1
1e8ee6: lea rdx, [rbp - 0x20]
1e8eea: mov r9d, edi
1e8eed: mov r8d, edi
1e8ef0: mov rcx, r12
1e8ef3: call 0x40ede0
1e8ef8: lea rdx, [rip + 0x4028ae] ; b''
1e8eff: mov rcx, r15
1e8f02: call 0x3fd810
1e8f07: mov rax, qword ptr [rip + 0x47e63a] ; b''
1e8f0e: mov rcx, qword ptr [rax + 0x1090]
1e8f15: cmp dword ptr [rcx + 0x7e54], 0
1e8f1c: je 0x1e8f2d
1e8f1e: cmp dword ptr [rcx + 0x7d98], 0
1e8f25: je 0x1e8f2d
1e8f27: mov eax, edi
1e8f29: xor esi, esi
1e8f2b: jmp 0x1e8f31
1e8f2d: xor esi, esi
1e8f2f: mov eax, esi
1e8f31: mov dword ptr [r14 + 0x80], 0x20002
1e8f3c: lea rcx, [rbp - 0x20]
1e8f40: test eax, eax
1e8f42: je 0x1e8f6f
1e8f44: lea rdx, [rip + 0x3b0685] ; b'sprdrdex'
1e8f4b: call 0x3ff7c0
1e8f50: mov r9d, edi
1e8f53: lea rdx, [rbp - 0x20]
1e8f57: mov r8d, edi
1e8f5a: lea rcx, [r14 + 0x198]
1e8f61: call 0x14d080
1e8f66: mov dword ptr [r14 + 0x260], edi
1e8f6d: jmp 0x1e8f91
1e8f6f: lea rdx, [rip + 0x3b066a] ; b'sprdrde2'
1e8f76: call 0x3ff7c0
1e8f7b: mov r9d, edi
1e8f7e: lea rdx, [rbp - 0x20]
1e8f82: mov r8d, edi
1e8f85: lea rcx, [r14 + 0x198]
1e8f8c: call 0x14d080
1e8f91: xor edx, edx
1e8f93: mov rcx, r13
1e8f96: call 0x412380
1e8f9b: xor edx, edx
1e8f9d: mov rcx, r13
1e8fa0: call 0x411610
1e8fa5: mov word ptr [r14 + 0x1f8], si
1e8fad: jmp 0x1e9623
1e8fb2: lea rdx, [rip + 0x3b05e7] ; b'EFF_M21'
1e8fb9: lea rcx, [rbp - 0x20]
1e8fbd: call 0x3ff7c0
1e8fc2: mov ebx, 1
1e8fc7: lea rdx, [rbp - 0x20]
1e8fcb: mov r9d, ebx
1e8fce: mov r8d, ebx
1e8fd1: mov rcx, r12
1e8fd4: call 0x40ede0
1e8fd9: lea rdx, [rip + 0x4027cd] ; b''
1e8fe0: mov rcx, r15
1e8fe3: call 0x3fd810
1e8fe8: mov rax, qword ptr [rip + 0x47e559] ; b''
1e8fef: mov rcx, qword ptr [rax + 0x1090]
1e8ff6: cmp dword ptr [rcx + 0x7e54], edi
1e8ffc: je 0x1e900d
1e8ffe: cmp dword ptr [rcx + 0x7d98], edi
1e9004: je 0x1e900d
1e9006: mov dword ptr [r14 + 0x260], ebx
1e900d: xor edx, edx
1e900f: mov dword ptr [r14 + 0x80], 0x40004
1e901a: mov rcx, r13
1e901d: call 0x412380
1e9022: xor edx, edx
1e9024: mov rcx, r13
1e9027: call 0x411610
1e902c: mov word ptr [r14 + 0x1f8], di
1e9034: jmp 0x1e9623
1e9039: lea rdx, [rip + 0x3b05b0] ; b'EFF_M18a'
1e9040: lea rcx, [rbp - 0x20]
1e9044: call 0x3ff7c0
1e9049: mov ebx, 1
1e904e: lea rdx, [rbp - 0x20]
1e9052: mov r9d, ebx
1e9055: mov r8d, ebx
1e9058: mov rcx, r12
1e905b: call 0x40ede0
1e9060: lea rdx, [rip + 0x3b0599] ; b'ARE_M02'
1e9067: mov rcx, r15
1e906a: call 0x3fd810
1e906f: mov dword ptr [r14 + 0x258], ebx
1e9076: mov dword ptr [r14 + 0x80], 0x5200520
1e9081: movzx eax, byte ptr [rip + 0x3b1f78] ; b'\x10\x0c\xff\x05@\x01\x01'
1e9088: shl ax, 2
1e908c: mov word ptr [r14 + 0x8c], ax
1e9094: jmp 0x1e961c
1e9099: movzx ecx, byte ptr [rip + 0x3b1f60] ; b'\x10\x0c\xff\x05@\x01\x01'
1e90a0: lea rdx, [rip + 0x3b0561] ; b'EFF_M34'
1e90a7: movzx eax, cx
1e90aa: shl ax, 3
1e90ae: add cx, ax
1e90b1: mov word ptr [r14 + 0x8c], cx
1e90b9: lea rcx, [rbp - 0x20]
1e90bd: call 0x3ff7c0
1e90c2: mov edi, 1
1e90c7: lea rdx, [rbp - 0x20]
1e90cb: mov r9d, edi
1e90ce: mov r8d, edi
1e90d1: mov rcx, r12
1e90d4: call 0x40ede0
1e90d9: lea rdx, [rip + 0x3b0530] ; b'ARE_M04'
1e90e0: mov rcx, r15
1e90e3: call 0x3fd810
1e90e8: lea rdx, [rip + 0x3b04c5] ; b'SPBOOM'
1e90ef: mov dword ptr [r14 + 0x258], edi
1e90f6: lea rcx, [rbp - 0x20]
1e90fa: mov dword ptr [r14 + 0x80], 0x6100600
1e9105: call 0x3ff7c0
1e910a: lea rcx, [r14 + 0x198]
1e9111: mov r9d, edi
1e9114: mov r8d, edi
1e9117: lea rdx, [rbp - 0x20]
1e911b: call 0x14d080
1e9120: lea rdx, [r14 + 0x1c8]
1e9127: mov rcx, r13
1e912a: call 0x412390
1e912f: xor edx, edx
1e9131: mov rcx, r13
1e9134: call 0x412380
1e9139: xor edx, edx
1e913b: mov rcx, r13
1e913e: call 0x411610
1e9143: mov qword ptr [r14 + 0x260], rdi
1e914a: jmp 0x1e9623
1e914f: movzx ecx, byte ptr [rip + 0x3b1eaa] ; b'\x10\x0c\xff\x05@\x01\x01'
1e9156: lea rdx, [rip + 0x3b04bb] ; b'EFF_M31b'
1e915d: movzx eax, cx
1e9160: shl ax, 2
1e9164: add cx, ax
1e9167: mov word ptr [r14 + 0x8c], cx
1e916f: lea rcx, [rbp - 0x20]
1e9173: call 0x3ff7c0
1e9178: mov ebx, 1
1e917d: lea rdx, [rbp - 0x20]
1e9181: mov r9d, ebx
1e9184: mov r8d, ebx
1e9187: mov rcx, r12
1e918a: call 0x40ede0
1e918f: lea rdx, [rip + 0x3b0492] ; b'ARE_M01'
1e9196: mov rcx, r15
1e9199: call 0x3fd810
1e919e: mov dword ptr [r14 + 0x258], ebx
1e91a5: mov dword ptr [r14 + 0x80], 0x7100700
1e91b0: jmp 0x1e9623
1e91b5: movzx eax, byte ptr [rip + 0x3b1e44] ; b'\x10\x0c\xff\x05@\x01\x01'
1e91bc: lea rdx, [rip + 0x3b046d] ; b'EFF_M19'
1e91c3: shl ax, 2
1e91c7: lea rcx, [rbp - 0x20]
1e91cb: mov word ptr [r14 + 0x8c], ax
1e91d3: call 0x3ff7c0
1e91d8: mov ebx, 1
1e91dd: lea rdx, [rbp - 0x20]
1e91e1: mov r9d, ebx
1e91e4: mov r8d, ebx
1e91e7: mov rcx, r12
1e91ea: call 0x40ede0
1e91ef: lea rdx, [rip + 0x3b0442] ; b'ARE_M03'
1e91f6: mov rcx, r15
1e91f9: call 0x3fd810
1e91fe: mov dword ptr [r14 + 0x258], ebx
1e9205: mov dword ptr [r14 + 0x80], 0x8100800
1e9210: jmp 0x1e9623
1e9215: movzx eax, byte ptr [rip + 0x3b1de4] ; b'\x10\x0c\xff\x05@\x01\x01'
1e921c: lea rdx, [rip + 0x3b03e5] ; b'EFF_M34'
1e9223: imul eax, eax, 0xf
1e9226: lea rcx, [rbp - 0x20]
1e922a: mov word ptr [r14 + 0x8c], ax
1e9232: call 0x3ff7c0
1e9237: mov ebx, 1
1e923c: lea rdx, [rbp - 0x20]
1e9240: mov r9d, ebx
1e9243: mov r8d, ebx
1e9246: mov rcx, r12
1e9249: call 0x40ede0
1e924e: lea rdx, [rip + 0x3b03eb] ; b'ARE_P14'
1e9255: mov rcx, r15
1e9258: call 0x3fd810
1e925d: mov dword ptr [r14 + 0x258], ebx
1e9264: mov dword ptr [r14 + 0x80], 0x9100900
1e926f: mov qword ptr [r14 + 0x260], rbx
1e9276: jmp 0x1e9623
1e927b: movzx ecx, byte ptr [rip + 0x3b1d7e] ; b'\x10\x0c\xff\x05@\x01\x01'
1e9282: lea rdx, [rip + 0x402524] ; b''
1e9289: movzx eax, cx
1e928c: shl ax, 2
1e9290: add cx, ax
1e9293: mov word ptr [r14 + 0x8c], cx
1e929b: mov rcx, r15
1e929e: call 0x3fd810
1e92a3: mov ecx, 1
1e92a8: mov dword ptr [r14 + 0x80], 0xc100c00
1e92b3: mov dword ptr [r14 + 0x258], ecx
1e92ba: mov qword ptr [r14 + 0x260], rcx
1e92c1: jmp 0x1e9623
1e92c6: movzx eax, byte ptr [rip + 0x3b1d33] ; b'\x10\x0c\xff\x05@\x01\x01'
1e92cd: lea rdx, [rip + 0x3b0334] ; b'EFF_M34'
1e92d4: shl ax, 2
1e92d8: lea rcx, [rbp - 0x20]
1e92dc: mov word ptr [r14 + 0x8c], ax
1e92e4: call 0x3ff7c0
1e92e9: mov ebx, 1
1e92ee: lea rdx, [rbp - 0x20]
1e92f2: mov r9d, ebx
1e92f5: mov r8d, ebx
1e92f8: mov rcx, r12
1e92fb: call 0x40ede0
1e9300: lea rdx, [rip + 0x4024a6] ; b''
1e9307: mov rcx, r15
1e930a: call 0x3fd810
1e930f: lea rdx, [rip + 0x3b0332] ; b'SPHORWIL'
1e9316: mov dword ptr [r14 + 0x80], 0xa100a00
1e9321: lea rcx, [rbp - 0x20]
1e9325: call 0x3ff7c0
1e932a: lea rcx, [r14 + 0x198]
1e9331: mov r9d, ebx
1e9334: mov r8d, ebx
1e9337: lea rdx, [rbp - 0x20]
1e933b: call 0x14d080
1e9340: xor edx, edx
1e9342: mov rcx, r13
1e9345: call 0x412380
1e934a: xor edx, edx
1e934c: mov rcx, r13
1e934f: call 0x411610
1e9354: mov qword ptr [r14 + 0x260], rbx
1e935b: jmp 0x1e9623
1e9360: movzx ecx, byte ptr [rip + 0x3b1c99] ; b'\x10\x0c\xff\x05@\x01\x01'
1e9367: lea rdx, [rip + 0x3b029a] ; b'EFF_M34'
1e936e: movzx eax, cx
1e9371: shl ax, 2
1e9375: add cx, ax
1e9378: mov word ptr [r14 + 0x8c], cx
1e9380: lea rcx, [rbp - 0x20]
1e9384: call 0x3ff7c0
1e9389: mov ebx, 1
1e938e: lea rdx, [rbp - 0x20]
1e9392: mov r9d, ebx
1e9395: mov r8d, ebx
1e9398: mov rcx, r12
1e939b: call 0x40ede0
1e93a0: lea rdx, [rip + 0x3b02b1] ; b'ARE_M11'
1e93a7: mov rcx, r15
1e93aa: call 0x3fd810
1e93af: lea rdx, [rip + 0x3b02aa] ; b'SPWRDFLD'
1e93b6: mov dword ptr [r14 + 0x258], ebx
1e93bd: mov dword ptr [r14 + 0x80], 0xa110a01
1e93c8: jmp 0x1e9321
1e93cd: movzx eax, byte ptr [rip + 0x3b1c2c] ; b'\x10\x0c\xff\x05@\x01\x01'
1e93d4: lea rdx, [rip + 0x3b0255] ; b'EFF_M19'
1e93db: shl ax, 2
1e93df: lea rcx, [rbp - 0x20]
1e93e3: mov word ptr [r14 + 0x8c], ax
1e93eb: call 0x3ff7c0
1e93f0: mov ebx, 1
1e93f5: lea rdx, [rbp - 0x20]
1e93f9: mov r9d, ebx
1e93fc: mov r8d, ebx
1e93ff: mov rcx, r12
1e9402: call 0x40ede0
1e9407: lea rdx, [rip + 0x3b0262] ; b'ARE_P01'
1e940e: mov rcx, r15
1e9411: call 0x3fd810
1e9416: lea rdx, [rip + 0x3b025b] ; b'SPgflsh1'
1e941d: mov dword ptr [r14 + 0x258], ebx
1e9424: lea rcx, [rbp - 0x20]
1e9428: mov dword ptr [r14 + 0x80], 0xa120a02
1e9433: call 0x3ff7c0
1e9438: lea rcx, [r14 + 0x198]
1e943f: mov r9d, ebx
1e9442: mov r8d, ebx
1e9445: lea rdx, [rbp - 0x20]
1e9449: call 0x14d080
1e944e: xor edx, edx
1e9450: mov rcx, r13
1e9453: call 0x412380
1e9458: xor edx, edx
1e945a: mov rcx, r13
1e945d: call 0x411610
1e9462: mov dword ptr [r14 + 0x25c], ebx
1e9469: mov qword ptr [r14 + 0x260], rbx
1e9470: jmp 0x1e9623
1e9475: lea rdx, [rip + 0x3b01b4] ; b'EFF_M19'
1e947c: lea rcx, [rbp - 0x20]
1e9480: call 0x3ff7c0
1e9485: mov ebx, 1
1e948a: lea rdx, [rbp - 0x20]
1e948e: mov r9d, ebx
1e9491: mov r8d, ebx
1e9494: mov rcx, r12
1e9497: call 0x40ede0
1e949c: lea rdx, [rip + 0x40230a] ; b''
1e94a3: mov rcx, r15
1e94a6: call 0x3fd810
1e94ab: mov dword ptr [r14 + 0x80], 0xb030b03
1e94b6: jmp 0x1e9615
1e94bb: movzx ecx, byte ptr [rip + 0x3b1b3e] ; b'\x10\x0c\xff\x05@\x01\x01'
1e94c2: lea rdx, [rip + 0x3b0167] ; b'EFF_M19'
1e94c9: movzx eax, cx
1e94cc: add ax, ax
1e94cf: add cx, ax
1e94d2: mov word ptr [r14 + 0x8c], cx
1e94da: lea rcx, [rbp - 0x20]
1e94de: call 0x3ff7c0
1e94e3: mov ebx, 1
1e94e8: lea rdx, [rbp - 0x20]
1e94ec: mov r9d, ebx
1e94ef: mov r8d, ebx
1e94f2: mov rcx, r12
1e94f5: call 0x40ede0
1e94fa: lea rdx, [rip + 0x4022ac] ; b''
1e9501: mov rcx, r15
1e9504: call 0x3fd810
1e9509: mov dword ptr [r14 + 0x80], 0xb010b01
1e9514: jmp 0x1e9615
1e9519: movzx eax, byte ptr [rip + 0x3b1ae0] ; b'\x10\x0c\xff\x05@\x01\x01'
1e9520: lea rdx, [rip + 0x3b00e1] ; b'EFF_M34'
1e9527: add ax, ax
1e952a: lea rcx, [rbp - 0x20]
1e952e: mov word ptr [r14 + 0x8c], ax
1e9536: call 0x3ff7c0
1e953b: mov ebx, 1
1e9540: lea rdx, [rbp - 0x20]
1e9544: mov r9d, ebx
1e9547: mov r8d, ebx
1e954a: mov rcx, r12
1e954d: call 0x40ede0
1e9552: lea rdx, [rip + 0x402254] ; b''
1e9559: mov rcx, r15
1e955c: call 0x3fd810
1e9561: mov dword ptr [r14 + 0x80], 0xa230a03
1e956c: mov qword ptr [r14 + 0x260], rbx
1e9573: jmp 0x1e9623
1e9578: movzx eax, byte ptr [rip + 0x3b1a81] ; b'\x10\x0c\xff\x05@\x01\x01'
1e957f: lea rdx, [rip + 0x3b0082] ; b'EFF_M34'
1e9586: add ax, ax
1e9589: lea rcx, [rbp - 0x20]
1e958d: mov word ptr [r14 + 0x8c], ax
1e9595: call 0x3ff7c0
1e959a: mov ebx, 1
1e959f: lea rdx, [rbp - 0x20]
1e95a3: mov r9d, ebx
1e95a6: mov r8d, ebx
1e95a9: mov rcx, r12
1e95ac: call 0x40ede0
1e95b1: lea rdx, [rip + 0x4021f5] ; b''
1e95b8: mov rcx, r15
1e95bb: call 0x3fd810
1e95c0: mov dword ptr [r14 + 0x80], 0xa240a04
1e95cb: mov qword ptr [r14 + 0x260], rbx
1e95d2: jmp 0x1e9623
1e95d4: lea rdx, [rip + 0x3b002d] ; b'EFF_M34'
1e95db: lea rcx, [rbp - 0x20]
1e95df: call 0x3ff7c0
1e95e4: mov ebx, 1
1e95e9: lea rdx, [rbp - 0x20]
1e95ed: mov r9d, ebx
1e95f0: mov r8d, ebx
1e95f3: mov rcx, r12
1e95f6: call 0x40ede0
1e95fb: lea rdx, [rip + 0x4021ab] ; b''
1e9602: mov rcx, r15
1e9605: call 0x3fd810
1e960a: mov dword ptr [r14 + 0x80], 0xb040b04
1e9615: mov dword ptr [r14 + 0x26c], ebx
1e961c: mov dword ptr [r14 + 0x260], ebx
1e9623: mov rax, r14
1e9626: mov rcx, qword ptr [rbp - 0x10]
1e962a: xor rcx, rsp
1e962d: call 0x4f77a0
1e9632: mov rbx, qword ptr [rsp + 0x88]
1e963a: add rsp, 0x40
1e963e: pop r15
1e9640: pop r14
1e9642: pop r13
1e9644: pop r12
1e9646: pop rdi
1e9647: pop rsi
1e9648: pop rbp
1e9649: ret 
1e964a: nop 
