1eaf90: mov qword ptr [rsp + 0x18], rbx
1eaf95: mov qword ptr [rsp + 0x20], rsi
1eaf9a: push rbp
1eaf9b: push rdi
1eaf9c: push r12
1eaf9e: push r13
1eafa0: push r14
1eafa2: lea rbp, [rsp - 0x37]
1eafa7: sub rsp, 0xa0
1eafae: mov rax, qword ptr [rip + 0x479a23] ; b'2\xa2\xdf-\x99+'
1eafb5: xor rax, rsp
1eafb8: mov qword ptr [rbp + 0x27], rax
1eafbc: mov rbx, qword ptr [rcx + 0x18]
1eafc0: xor r13d, r13d
1eafc3: mov r14, rcx
1eafc6: mov eax, dword ptr [rip + 0x3b7378] ; b'\x80'
1eafcc: mov esi, r13d
1eafcf: lea r12, [rbx + 0x5c8]
1eafd6: cmp dword ptr [rcx + 0x260], r13d
1eafdd: je 0x1eafe4
1eafdf: mov esi, eax
1eafe1: or esi, 8
1eafe4: cmp dword ptr [rcx + 0x25c], r13d
1eafeb: je 0x1eaff3
1eafed: bts eax, 9
1eaff1: jmp 0x1eaffc
1eaff3: mov eax, dword ptr [rip + 0x3b734f] ; b''
1eaff9: or eax, 1
1eaffc: or esi, eax
1eaffe: lea rdx, [rbp - 9]
1eb002: mov eax, dword ptr [rbx + 0x678]
1eb008: dec eax
1eb00a: mov dword ptr [rbp - 0x29], r13d
1eb00e: mov dword ptr [rbp - 0x25], eax
1eb011: mov eax, dword ptr [rcx + 0xc]
1eb014: lea rcx, [rbp - 0x29]
1eb018: mov dword ptr [rbp - 9], eax
1eb01b: call 0x407bb0
1eb020: lea rdx, [rbp - 0x25]
1eb024: mov dword ptr [rbp - 0x19], eax
1eb027: lea rcx, [rbp - 0x19]
1eb02b: call 0x407bc0
1eb030: mov dword ptr [rbp - 0x21], eax
1eb033: lea rdx, [rbp - 0x19]
1eb037: mov rax, qword ptr [r14 + 0x18]
1eb03b: mov ecx, dword ptr [rax + 0x67c]
1eb041: mov eax, dword ptr [r14 + 0x10]
1eb045: dec ecx
1eb047: mov dword ptr [rbp - 0x29], ecx
1eb04a: lea rcx, [rbp - 0x25]
1eb04e: mov dword ptr [rbp - 0x19], eax
1eb051: mov dword ptr [rbp - 0x25], r13d
1eb055: call 0x407bb0
1eb05a: lea rdx, [rbp - 0x29]
1eb05e: mov dword ptr [rbp - 9], eax
1eb061: lea rcx, [rbp - 9]
1eb065: call 0x407bc0
1eb06a: movzx ecx, byte ptr [rip + 0x3b3b7a] ; b' \x0f'
1eb071: mov dword ptr [rbp - 0x1d], eax
1eb074: cdq 
1eb075: idiv ecx
1eb077: movsx ecx, word ptr [rbx + 0xbbc]
1eb07e: movsx r8d, ax
1eb082: mov eax, dword ptr [rbp - 0x21]
1eb085: imul r8d, ecx
1eb089: cdq 
1eb08a: movzx ecx, byte ptr [rip + 0x3b3b59] ; b'  \x0f'
1eb091: idiv ecx
1eb093: add ax, r8w
1eb097: movsx rax, ax
1eb09b: test eax, eax
1eb09d: js 0x1eb2ab
1eb0a3: cmp eax, dword ptr [rbx + 0xbb8]
1eb0a9: jge 0x1eb2ab
1eb0af: mov rcx, rax
1eb0b2: mov rax, qword ptr [rbx + 0xbb0]
1eb0b9: movzx ecx, word ptr [rax + rcx*2]
1eb0bd: test word ptr [rip + 0x3b3b24], cx ; b'\xff\x7f  \x0f'
1eb0c4: je 0x1eb2ab
1eb0ca: lea rcx, [r14 + 0x1a0]
1eb0d1: lea rdx, [rip + 0x4006d5] ; b''
1eb0d8: call 0x3ffb60
1eb0dd: test eax, eax
1eb0df: je 0x1eb2ab
1eb0e5: lea rcx, [r14 + 0x90]
1eb0ec: mov qword ptr [rsp + 0xd8], r15
1eb0f4: call 0x411df0
1eb0f9: test eax, eax
1eb0fb: jne 0x1eb2a3
1eb101: lea rdx, [rbp - 0x11]
1eb105: lea rcx, [r14 + 0x90]
1eb10c: call 0x411660
1eb111: lea rdx, [rbp - 1]
1eb115: lea rcx, [r14 + 0x90]
1eb11c: call 0x411780
1eb121: mov eax, dword ptr [rbp - 1]
1eb124: lea rdx, [r14 + 0xc]
1eb128: movzx r8d, byte ptr [r14 + 0x28]
1eb12d: mov rcx, qword ptr [r14 + 0x18]
1eb131: mov dword ptr [rbp + 0xf], eax
1eb134: mov eax, dword ptr [rbp + 3]
1eb137: mov dword ptr [rbp + 0x13], eax
1eb13a: mov eax, dword ptr [r14 + 0xc]
1eb13e: mov dword ptr [rbp - 0x21], eax
1eb141: mov qword ptr [rbp + 7], r13
1eb145: call 0x180c10
1eb14a: mov edx, dword ptr [r14 + 0x10]
1eb14e: lea r9, [rbp - 0x21]
1eb152: mov ecx, dword ptr [rbp - 0x21]
1eb155: add edx, eax
1eb157: sub ecx, dword ptr [rbp - 0x11]
1eb15a: mov r8d, esi
1eb15d: mov ebx, dword ptr [r14 + 0x14]
1eb161: mov eax, ecx
1eb163: sub eax, dword ptr [rbp + 7]
1eb166: add eax, dword ptr [rbp + 0xf]
1eb169: mov dword ptr [rbp - 0x1d], edx
1eb16c: sub edx, dword ptr [rbp - 0xd]
1eb16f: add ebx, edx
1eb171: mov dword ptr [rbp - 0x29], eax
1eb174: lea rax, [rbp - 0x11]
1eb178: mov dword ptr [rbp - 0x25], ecx
1eb17b: mov r13d, ebx
1eb17e: mov qword ptr [rsp + 0x20], rax
1eb183: sub r13d, dword ptr [rbp + 0xb]
1eb187: lea rdx, [rbp + 7]
1eb18b: add r13d, dword ptr [rbp + 0x13]
1eb18f: mov rcx, r12
1eb192: mov dword ptr [rbp - 0x19], ebx
1eb195: call 0x29e1b0
1eb19a: mov r8d, esi
1eb19d: lea rdx, [rbp + 7]
1eb1a1: mov rcx, r12
1eb1a4: call 0x29e190
1eb1a9: test eax, eax
1eb1ab: je 0x1eb2a3
1eb1b1: cmp dword ptr [r14 + 0x288], 0
1eb1b9: je 0x1eb1fd
1eb1bb: mov rcx, qword ptr [r14 + 0x390]
1eb1c2: call 0x3f6d50
1eb1c7: mov rbx, qword ptr [r14 + 0x390]
1eb1ce: mov rcx, rbx
1eb1d1: call 0x3f7890
1eb1d6: mov rcx, rbx
1eb1d9: mov edi, eax
1eb1db: call 0x3f78b0
1eb1e0: movzx r9d, word ptr [rip + 0x3d5490] ; b''
1eb1e8: lea rcx, [r14 + 0x90]
1eb1ef: mov rdx, rax
1eb1f2: mov r8d, edi
1eb1f5: call 0x4123c0
1eb1fa: mov ebx, dword ptr [rbp - 0x19]
1eb1fd: mov r9d, dword ptr [rbp - 0xd]
1eb201: lea rdx, [r14 + 0x90]
1eb208: mov r8d, dword ptr [rbp - 0x11]
1eb20c: xor edi, edi
1eb20e: mov dword ptr [rsp + 0x28], edi
1eb212: mov rcx, r12
1eb215: mov dword ptr [rsp + 0x20], esi
1eb219: call 0x29e260
1eb21e: mov r9d, dword ptr [r14 + 0x14]
1eb222: mov rcx, r12
1eb225: mov eax, dword ptr [rbp - 0x25]
1eb228: sub ebx, r9d
1eb22b: mov r8d, dword ptr [rbp - 0x1d]
1eb22f: sub r13d, r9d
1eb232: mov edx, dword ptr [rbp - 0x21]
1eb235: sub r8d, r9d
1eb238: mov dword ptr [rbp + 0x17], eax
1eb23b: mov eax, dword ptr [rbp - 0x29]
1eb23e: mov dword ptr [rbp + 0x1f], eax
1eb241: lea rax, [rbp + 0x17]
1eb245: mov dword ptr [rsp + 0x38], esi
1eb249: mov byte ptr [rsp + 0x30], dil
1eb24e: mov qword ptr [rsp + 0x28], rax
1eb253: lea rax, [rbp - 0x11]
1eb257: mov qword ptr [rsp + 0x20], rax
1eb25c: mov dword ptr [rbp + 0x1b], ebx
1eb25f: mov dword ptr [rbp + 0x23], r13d
1eb263: call 0x29e4c0
1eb268: lea r9, [rbp - 0x19]
1eb26c: mov qword ptr [rbp - 0x19], rdi
1eb270: xor r8d, r8d
1eb273: mov edx, esi
1eb275: mov rcx, r12
1eb278: call 0x29ea40
1eb27d: mov eax, dword ptr [rbp - 0xd]
1eb280: lea rdx, [rbp + 7]
1eb284: mov r9d, dword ptr [rbp - 0x1d]
1eb288: mov rcx, r12
1eb28b: mov r8d, dword ptr [rbp - 0x21]
1eb28f: mov dword ptr [rsp + 0x30], esi
1eb293: mov dword ptr [rsp + 0x28], eax
1eb297: mov eax, dword ptr [rbp - 0x11]
1eb29a: mov dword ptr [rsp + 0x20], eax
1eb29e: call 0x29df60
1eb2a3: mov r15, qword ptr [rsp + 0xd8]
1eb2ab: mov rcx, qword ptr [rbp + 0x27]
1eb2af: xor rcx, rsp
1eb2b2: call 0x4f77a0
1eb2b7: lea r11, [rsp + 0xa0]
1eb2bf: mov rbx, qword ptr [r11 + 0x40]
1eb2c3: mov rsi, qword ptr [r11 + 0x48]
1eb2c7: mov rsp, r11
1eb2ca: pop r14
1eb2cc: pop r13
1eb2ce: pop r12
1eb2d0: pop rdi
1eb2d1: pop rbp
1eb2d2: ret 
1eb2d3: int3 
1eb2d4: int3 
1eb2d5: int3 
1eb2d6: int3 
1eb2d7: int3 
1eb2d8: int3 
1eb2d9: int3 
1eb2da: int3 
1eb2db: int3 
1eb2dc: int3 
1eb2dd: int3 
