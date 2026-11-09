2352f0: mov r11, rsp
2352f3: push rbp
2352f4: push rdi
2352f5: lea rbp, [r11 - 0x5f]
2352f9: sub rsp, 0xc8
235300: mov rax, qword ptr [rip + 0x42f6d1] ; b'2\xa2\xdf-\x99+'
235307: xor rax, rsp
23530a: mov qword ptr [rbp + 0x2f], rax
23530e: mov rdi, rcx
235311: mov rcx, qword ptr [rcx + 0x18]
235315: test rcx, rcx
235318: je 0x23568f
23531e: mov r8d, dword ptr [rcx + 0x688]
235325: mov edx, dword ptr [rcx + 0x68c]
23532b: mov eax, dword ptr [rcx + 0x648]
235331: mov qword ptr [r11 + 0x10], rbx
235335: mov qword ptr [r11 + 0x18], rsi
235339: mov qword ptr [r11 - 0x18], r13
23533d: lea r13, [rcx + 0x5c8]
235344: sub eax, dword ptr [r13 + 0x78]
235348: add eax, r8d
23534b: mov dword ptr [rbp - 0x19], edx
23534e: mov dword ptr [rbp - 0x25], eax
235351: mov eax, dword ptr [r13 + 0x84]
235358: sub eax, dword ptr [r13 + 0x7c]
23535c: add eax, edx
23535e: mov dword ptr [rbp - 0x21], r8d
235362: movzx r8d, byte ptr [rdi + 0x28]
235367: lea rdx, [rdi + 0xc]
23536b: mov dword ptr [rbp - 0x1d], eax
23536e: mov eax, dword ptr [rdx]
235370: mov dword ptr [rbp - 0x39], eax
235373: mov qword ptr [r11 - 0x28], r15
235377: call 0x180c10
23537c: mov edx, dword ptr [rdi + 0x10]
23537f: add edx, eax
235381: mov dword ptr [rbp - 0x35], edx
235384: mov eax, dword ptr [r13 + 0xb4]
23538b: cmp edx, eax
23538d: jl 0x235394
23538f: dec eax
235391: mov dword ptr [rbp - 0x35], eax
235394: mov rbx, qword ptr [rbp - 0x39]
235398: mov rcx, qword ptr [rdi + 0x1b8]
23539f: mov qword ptr [rbp + 7], rbx
2353a3: call 0x411af0
2353a8: test dword ptr [rdi + 0x188], 0x20000
2353b2: movzx ecx, ax
2353b5: mov rax, qword ptr [rdi + 0x1b8]
2353bc: mov dword ptr [rbp - 0x29], ecx
2353bf: movzx r15d, word ptr [rax + 0x11a]
2353c7: mov dword ptr [rbp - 0xd], r15d
2353cb: mov esi, r15d
2353ce: je 0x2353e1
2353d0: mov eax, 0xaaaaaaab
2353d5: mul ecx
2353d7: mov ecx, edx
2353d9: shr ecx, 1
2353db: add ecx, r15d
2353de: mov dword ptr [rbp - 0x29], ecx
2353e1: cmp r15d, ecx
2353e4: jge 0x23565f
2353ea: mov qword ptr [rsp + 0xb8], r14
2353f2: mov qword ptr [rsp + 0xf8], r12
2353fa: nop word ptr [rax + rax]
235400: mov rax, qword ptr [rdi]
235403: mov rcx, rdi
235406: call qword ptr [rax + 0xf8]
23540c: mov r14d, eax
23540f: mov eax, dword ptr [rbp - 0x35]
235412: test eax, eax
235414: js 0x23564b
23541a: movzx ecx, byte ptr [rip + 0x3697ca] ; b' \x0f'
235421: cdq 
235422: mov r9, qword ptr [rdi + 0x18]
235426: idiv ecx
235428: movsx ecx, word ptr [r9 + 0xbbc]
235430: movsx r8d, ax
235434: mov eax, dword ptr [rbp - 0x39]
235437: imul r8d, ecx
23543b: cdq 
23543c: movzx ecx, byte ptr [rip + 0x3697a7] ; b'  \x0f'
235443: idiv ecx
235445: add ax, r8w
235449: movsx rax, ax
23544d: test eax, eax
23544f: js 0x23564b
235455: cmp eax, dword ptr [r9 + 0xbb8]
23545c: jge 0x23564b
235462: mov rcx, rax
235465: mov rax, qword ptr [r9 + 0xbb0]
23546c: movzx ecx, word ptr [rax + rcx*2]
235470: test word ptr [rip + 0x369771], cx ; b'\xff\x7f  \x0f'
235477: je 0x23564b
23547d: mov rcx, qword ptr [rdi + 0x1b8]
235484: movzx edx, si
235487: call 0x412380
23548c: mov rcx, qword ptr [rdi + 0x1b8]
235493: lea rdx, [rbp - 0x31]
235497: call 0x411660
23549c: mov rcx, qword ptr [rdi + 0x1b8]
2354a3: lea rdx, [rbp - 9]
2354a7: call 0x411780
2354ac: mov r8d, dword ptr [rbp - 5]
2354b0: mov rax, qword ptr [rbp - 9]
2354b4: mov r12d, dword ptr [rdi + 0x14]
2354b8: sub r12d, dword ptr [rbp - 0x2d]
2354bc: add r12d, dword ptr [rbp - 0x35]
2354c0: mov r15d, dword ptr [rbp - 0x39]
2354c4: sub r15d, dword ptr [rbp - 0x31]
2354c8: mov dword ptr [rbp + 0x1b], r8d
2354cc: lea r9d, [r12 + r8]
2354d0: mov qword ptr [rbp + 0xf], 0
2354d8: mov r8d, dword ptr [rbp - 0x25]
2354dc: mov dword ptr [rbp + 0x17], eax
2354df: lea edx, [r15 + rax]
2354e3: mov dword ptr [rbp - 0x15], edx
2354e6: mov dword ptr [rbp - 0x11], r9d
2354ea: cmp r15d, r8d
2354ed: jge 0x23564b
2354f3: mov eax, dword ptr [rbp - 0x21]
2354f6: cmp edx, eax
2354f8: jl 0x23564b
2354fe: mov r10d, dword ptr [rbp - 0x1d]
235502: cmp r12d, r10d
235505: jge 0x23564b
23550b: mov r11d, dword ptr [rbp - 0x19]
23550f: cmp r9d, r11d
235512: jl 0x23564b
235518: cmp r15d, eax
23551b: mov ecx, eax
23551d: mov eax, r8d
235520: cmovge ecx, r15d
235524: cmp r8d, edx
235527: mov r8d, r10d
23552a: cmovge eax, edx
23552d: cmp r12d, r11d
235530: mov edx, r11d
235533: cmovge edx, r12d
235537: cmp r10d, r9d
23553a: cmovge r8d, r9d
23553e: cmp eax, ecx
235540: jle 0x23564b
235546: cmp r8d, edx
235549: jle 0x23564b
23554f: lea rax, [rbp - 0x31]
235553: bts r14d, 0x1b
235558: mov r8d, r14d
23555b: mov qword ptr [rsp + 0x20], rax
235560: lea r9, [rbp - 0x39]
235564: mov rcx, r13
235567: lea rdx, [rbp + 0xf]
23556b: call 0x29e1b0
235570: mov r8d, r14d
235573: lea rdx, [rbp + 0xf]
235577: mov rcx, r13
23557a: call 0x29e190
23557f: test eax, eax
235581: je 0x23563a
235587: mov r9d, dword ptr [rbp - 0x2d]
23558b: mov rcx, r13
23558e: mov r8d, dword ptr [rbp - 0x31]
235592: mov rdx, qword ptr [rdi + 0x1b8]
235599: mov dword ptr [rsp + 0x28], 0
2355a1: mov dword ptr [rsp + 0x20], r14d
2355a6: call 0x29e260
2355ab: mov ecx, dword ptr [rdi + 0x14]
2355ae: mov edx, ebx
2355b0: mov r8d, dword ptr [rbp + 0xb]
2355b4: mov r9d, ecx
2355b7: mov dword ptr [rsp + 0x38], r14d
2355bc: add r8d, ecx
2355bf: mov byte ptr [rsp + 0x30], 0
2355c4: neg r9d
2355c7: lea eax, [r12 + rcx]
2355cb: mov dword ptr [rbp + 0x1f], r15d
2355cf: mov dword ptr [rbp + 0x23], eax
2355d2: mov eax, dword ptr [rbp - 0x15]
2355d5: mov dword ptr [rbp + 0x27], eax
2355d8: mov eax, dword ptr [rbp - 0x11]
2355db: add eax, ecx
2355dd: mov rcx, r13
2355e0: mov dword ptr [rbp + 0x2b], eax
2355e3: lea rax, [rbp + 0x1f]
2355e7: mov qword ptr [rsp + 0x28], rax
2355ec: lea rax, [rbp - 0x31]
2355f0: mov qword ptr [rsp + 0x20], rax
2355f5: call 0x29e4c0
2355fa: xor r15d, r15d
2355fd: lea r9, [rbp - 1]
235601: xor r8d, r8d
235604: mov qword ptr [rbp - 1], r15
235608: mov edx, r14d
23560b: mov rcx, r13
23560e: call 0x29ea40
235613: mov eax, dword ptr [rbp - 0x2d]
235616: lea rdx, [rbp + 0xf]
23561a: mov r9d, dword ptr [rbp - 0x35]
23561e: mov rcx, r13
235621: mov r8d, dword ptr [rbp - 0x39]
235625: mov dword ptr [rsp + 0x30], r14d
23562a: mov dword ptr [rsp + 0x28], eax
23562e: mov eax, dword ptr [rbp - 0x31]
235631: mov dword ptr [rsp + 0x20], eax
235635: call 0x29df60
23563a: mov eax, dword ptr [rbp - 0x2d]
23563d: inc esi
23563f: sub dword ptr [rbp - 0x35], eax
235642: cmp esi, dword ptr [rbp - 0x29]
235645: jl 0x235400
23564b: mov r15d, dword ptr [rbp - 0xd]
23564f: mov r14, qword ptr [rsp + 0xb8]
235657: mov r12, qword ptr [rsp + 0xf8]
23565f: mov rcx, qword ptr [rdi + 0x1b8]
235666: movzx edx, r15w
23566a: call 0x412380
23566f: mov r15, qword ptr [rsp + 0xb0]
235677: mov r13, qword ptr [rsp + 0xc0]
23567f: mov rsi, qword ptr [rsp + 0xf0]
235687: mov rbx, qword ptr [rsp + 0xe8]
23568f: mov rcx, qword ptr [rbp + 0x2f]
235693: xor rcx, rsp
235696: call 0x4f77a0
23569b: add rsp, 0xc8
2356a2: pop rdi
2356a3: pop rbp
2356a4: ret 
2356a5: int3 
2356a6: int3 
2356a7: int3 
2356a8: int3 
2356a9: int3 
2356aa: int3 
2356ab: int3 
2356ac: int3 
2356ad: int3 
2356ae: int3 
2356af: int3 
