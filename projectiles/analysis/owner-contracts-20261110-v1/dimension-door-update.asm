22a060: push rbx
22a062: sub rsp, 0x40
22a066: mov rax, qword ptr [rip + 0x43a96b] ; b'2\xa2\xdf-\x99+'
22a06d: xor rax, rsp
22a070: mov qword ptr [rsp + 0x30], rax
22a075: mov rax, qword ptr [rip + 0x43d4cc] ; b''
22a07c: mov rbx, rcx
22a07f: mov rcx, qword ptr [rax + 0x1090]
22a086: cmp dword ptr [rcx + 0x9690], 0
22a08d: je 0x22a09e
22a08f: mov eax, dword ptr [rbx + 0x48]
22a092: cmp dword ptr [rcx + 0x9694], eax
22a098: jne 0x22a1d5
22a09e: movzx eax, byte ptr [rbx + 0x420]
22a0a5: mov qword ptr [rsp + 0x58], rdi
22a0aa: test al, al
22a0ac: je 0x22a1e8
22a0b2: cmp al, 3
22a0b4: jbe 0x22a185
22a0ba: cmp al, 4
22a0bc: je 0x22a0f2
22a0be: cmp al, 5
22a0c0: jne 0x22a1b9
22a0c6: movzx eax, word ptr [rbx + 0x2d0]
22a0cd: test ax, ax
22a0d0: jne 0x22a0e3
22a0d2: mov rax, qword ptr [rbx]
22a0d5: mov rcx, rbx
22a0d8: call qword ptr [rax + 0xd8]
22a0de: jmp 0x22a1d0
22a0e3: dec ax
22a0e6: mov word ptr [rbx + 0x2d0], ax
22a0ed: jmp 0x22a1b9
22a0f2: lea rdi, [rbx + 0x1b8]
22a0f9: mov rcx, rdi
22a0fc: call 0x411df0
22a101: test eax, eax
22a103: je 0x22a17d
22a105: lea rdx, [rbx + 0x418]
22a10c: lea r8, [rip + 0x3e0b29] ; b'2'
22a113: lea rcx, [rsp + 0x28]
22a118: call 0x3fd8e0
22a11d: mov rdx, rax
22a120: lea rcx, [rsp + 0x20]
22a125: call 0x3ff710
22a12a: mov r9d, 1
22a130: lea rcx, [rbx + 0x2c0]
22a137: mov r8d, r9d
22a13a: lea rdx, [rsp + 0x20]
22a13f: call 0x14d080
22a144: lea rcx, [rsp + 0x28]
22a149: call 0x3fd740
22a14e: xor edx, edx
22a150: mov rcx, rdi
22a153: call 0x412380
22a158: movzx edx, word ptr [rdi + 0x11a]
22a15f: mov rcx, rdi
22a162: call 0x411cc0
22a167: movzx edx, al
22a16a: mov rcx, rdi
22a16d: dec dx
22a170: call 0x411610
22a175: inc byte ptr [rbx + 0x420]
22a17b: jmp 0x22a1b9
22a17d: mov rax, qword ptr [rdi]
22a180: mov rcx, rdi
22a183: jmp 0x22a1b7
22a185: lea rcx, [rbx + 0x1b8]
22a18c: call 0x411df0
22a191: test eax, eax
22a193: je 0x22a1a9
22a195: xor edx, edx
22a197: lea rcx, [rbx + 0x1b8]
22a19e: call 0x411610
22a1a3: inc byte ptr [rbx + 0x420]
22a1a9: mov rax, qword ptr [rbx + 0x1b8]
22a1b0: lea rcx, [rbx + 0x1b8]
22a1b7: call qword ptr [rax]
22a1b9: mov r9d, dword ptr [rbx + 0x14]
22a1bd: lea rcx, [rbx + 0x120]
22a1c4: mov r8d, dword ptr [rbx + 0x10]
22a1c8: mov edx, dword ptr [rbx + 0xc]
22a1cb: call 0x40eae0
22a1d0: mov rdi, qword ptr [rsp + 0x58]
22a1d5: mov rcx, qword ptr [rsp + 0x30]
22a1da: xor rcx, rsp
22a1dd: call 0x4f77a0
22a1e2: add rsp, 0x40
22a1e6: pop rbx
22a1e7: ret 
22a1e8: lea rcx, [rbx + 0x1b8]
22a1ef: call 0x411df0
22a1f4: test eax, eax
22a1f6: je 0x22a1a9
22a1f8: lea rdx, [rbx + 0x418]
22a1ff: lea r8, [rip + 0x3d5d32] ; b'1'
22a206: lea rcx, [rsp + 0x20]
22a20b: call 0x3fd8e0
22a210: mov rdx, rax
22a213: lea rcx, [rsp + 0x28]
22a218: call 0x3ff710
22a21d: mov r9d, 1
22a223: lea rcx, [rbx + 0x2c0]
22a22a: mov r8d, r9d
22a22d: lea rdx, [rsp + 0x28]
22a232: call 0x14d080
22a237: lea rcx, [rsp + 0x20]
22a23c: call 0x3fd740
22a241: xor edx, edx
22a243: lea rcx, [rbx + 0x1b8]
22a24a: call 0x412380
22a24f: xor edx, edx
22a251: lea rcx, [rbx + 0x1b8]
22a258: call 0x411610
22a25d: inc byte ptr [rbx + 0x420]
22a263: jmp 0x22a1b9
