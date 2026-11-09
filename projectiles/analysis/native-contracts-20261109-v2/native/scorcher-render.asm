234520: mov r11, rsp
234523: push rbp
234524: push rbx
234525: lea rbp, [r11 - 0x5f]
234529: sub rsp, 0xc8
234530: mov rax, qword ptr [rip + 0x4304a1] ; b'2\xa2\xdf-\x99+'
234537: xor rax, rsp
23453a: mov qword ptr [rbp + 0x27], rax
23453e: mov r9, qword ptr [rcx + 0x18]
234542: mov rbx, rcx
234545: test r9, r9
234548: je 0x234a06
23454e: mov qword ptr [r11 + 0x10], rsi
234552: lea rax, [r9 + 0x5c8]
234559: mov qword ptr [r11 + 0x20], r12
23455d: mov qword ptr [r11 - 0x20], r14
234561: mov qword ptr [r11 - 0x28], r15
234565: mov r15d, dword ptr [rcx + 0x118]
23456c: movsx ecx, word ptr [rcx + 0x216]
234573: mov qword ptr [rbp - 1], rax
234577: movzx eax, byte ptr [rip + 0x378915] ; b'\x08'
23457e: cmp ecx, eax
234580: jle 0x234589
234582: or r15d, dword ptr [rip + 0x36ddc3] ; b'\x10'
234589: cmp word ptr [rbx + 0x214], 5
234591: jne 0x2345b0
234593: movzx eax, byte ptr [rip + 0x3788f5] ; b'\x04'
23459a: cmp ecx, eax
23459c: jle 0x2345b0
23459e: movzx eax, byte ptr [rip + 0x3788f2] ; b'\x0c\xff\xff\x0e\x01\xe8\x03\x03\x05\x10'
2345a5: cmp ecx, eax
2345a7: jge 0x2345b0
2345a9: or r15d, dword ptr [rip + 0x36dda0] ; b' '
2345b0: mov eax, dword ptr [r9 + 0x688]
2345b7: mov ecx, dword ptr [r9 + 0x68c]
2345be: mov edx, dword ptr [r9 + 0x648]
2345c5: sub edx, dword ptr [r9 + 0x640]
2345cc: movzx r8d, byte ptr [rbx + 0x28]
2345d1: add edx, eax
2345d3: mov dword ptr [rbp - 0x1d], eax
2345d6: mov eax, dword ptr [r9 + 0x64c]
2345dd: sub eax, dword ptr [r9 + 0x644]
2345e4: add eax, ecx
2345e6: mov dword ptr [rbp - 0x15], ecx
2345e9: mov dword ptr [rbp - 0x19], eax
2345ec: mov rcx, r9
2345ef: mov eax, dword ptr [rbx + 0xc]
2345f2: mov dword ptr [rbp - 0x21], edx
2345f5: lea rdx, [rbx + 0xc]
2345f9: mov dword ptr [rbp - 0x39], eax
2345fc: call 0x180c10
234601: mov ecx, dword ptr [rbx + 0x10]
234604: lea rdx, [rbp - 0x29]
234608: sub ecx, dword ptr [rbx + 0x14]
23460b: add eax, ecx
23460d: mov rcx, qword ptr [rbx + 0x1b8]
234614: mov dword ptr [rbp - 0x35], eax
234617: call 0x411660
23461c: mov rcx, qword ptr [rbx + 0x1b8]
234623: lea rdx, [rbp - 0x11]
234627: call 0x411780
23462c: mov r11d, dword ptr [rbp - 0x11]
234630: xor r14d, r14d
234633: mov r10d, dword ptr [rbp - 0xd]
234637: xor esi, esi
234639: xor r12b, r12b
23463c: mov qword ptr [rbp + 7], r14
234640: mov dword ptr [rbp + 0xf], r11d
234644: mov dword ptr [rbp + 0x13], r10d
234648: cmp byte ptr [rbx + 0x3b8], sil
23464f: jbe 0x2349e6
234655: mov r9d, dword ptr [rbp - 0x35]
234659: mov qword ptr [rsp + 0xf0], rdi
234661: mov qword ptr [rsp + 0xc0], r13
234669: nop dword ptr [rax]
234670: movzx ecx, byte ptr [rip + 0x36a574] ; b' \x0f'
234677: mov eax, r9d
23467a: mov r13, qword ptr [rbx + 0x18]
23467e: cdq 
23467f: mov edi, dword ptr [rbp - 0x39]
234682: idiv ecx
234684: movsx ecx, word ptr [r13 + 0xbbc]
23468c: movsx r8d, ax
234690: mov eax, edi
234692: imul r8d, ecx
234696: cdq 
234697: movzx ecx, byte ptr [rip + 0x36a54c] ; b'  \x0f'
23469e: idiv ecx
2346a0: add ax, r8w
2346a4: movsx rax, ax
2346a8: test eax, eax
2346aa: js 0x23490b
2346b0: cmp eax, dword ptr [r13 + 0xbb8]
2346b7: jge 0x23490b
2346bd: mov rcx, rax
2346c0: mov rax, qword ptr [r13 + 0xbb0]
2346c7: movzx ecx, word ptr [rax + rcx*2]
2346cb: test word ptr [rip + 0x36a516], cx ; b'\xff\x7f  \x0f'
2346d2: je 0x23490b
2346d8: movsx ecx, word ptr [rbx + 0x216]
2346df: movzx eax, byte ptr [rip + 0x3787ad] ; b'\x08'
2346e6: cmp ecx, eax
2346e8: jle 0x2346f9
2346ea: mov r8d, r14d
2346ed: sub r8d, r11d
2346f0: add r8d, dword ptr [rbp - 0x29]
2346f4: add r8d, edi
2346f7: jmp 0x234700
2346f9: mov r8d, edi
2346fc: sub r8d, dword ptr [rbp - 0x29]
234700: cmp word ptr [rbx + 0x214], 5
234708: mov dword ptr [rbp + 0x17], r8d
23470c: jne 0x234731
23470e: movzx eax, byte ptr [rip + 0x37877a] ; b'\x04'
234715: cmp ecx, eax
234717: jle 0x234731
234719: movzx eax, byte ptr [rip + 0x378777] ; b'\x0c\xff\xff\x0e\x01\xe8\x03\x03\x05\x10'
234720: cmp ecx, eax
234722: jge 0x234731
234724: mov edx, esi
234726: sub edx, r10d
234729: add edx, dword ptr [rbp - 0x25]
23472c: add edx, r9d
23472f: jmp 0x234737
234731: mov edx, r9d
234734: sub edx, dword ptr [rbp - 0x25]
234737: sub r10d, esi
23473a: mov dword ptr [rbp + 0x1b], edx
23473d: mov esi, dword ptr [rbp - 0x21]
234740: sub r11d, r14d
234743: add r10d, edx
234746: mov dword ptr [rbp + 0x23], r10d
23474a: lea r9d, [r11 + r8]
23474e: mov dword ptr [rbp + 0x1f], r9d
234752: cmp r8d, esi
234755: jge 0x23490b
23475b: mov eax, dword ptr [rbp - 0x1d]
23475e: cmp r9d, eax
234761: jl 0x23490b
234767: mov r11d, dword ptr [rbp - 0x19]
23476b: cmp edx, r11d
23476e: jge 0x23490b
234774: mov edi, dword ptr [rbp - 0x15]
234777: cmp r10d, edi
23477a: jl 0x23490b
234780: cmp r8d, eax
234783: mov ecx, eax
234785: mov eax, esi
234787: cmovge ecx, r8d
23478b: cmp esi, r9d
23478e: mov r8d, edi
234791: cmovge eax, r9d
234795: cmp edx, edi
234797: cmovge r8d, edx
23479b: cmp r11d, r10d
23479e: mov edx, r11d
2347a1: cmovge edx, r10d
2347a5: cmp eax, ecx
2347a7: jle 0x23490b
2347ad: cmp edx, r8d
2347b0: jle 0x23490b
2347b6: mov rdi, qword ptr [rbp - 1]
2347ba: lea rax, [rbp - 0x29]
2347be: mov rcx, rdi
2347c1: mov qword ptr [rsp + 0x20], rax
2347c6: lea r9, [rbp - 0x39]
2347ca: mov r8d, r15d
2347cd: lea rdx, [rbp + 7]
2347d1: call 0x29e1b0
2347d6: mov r8d, r15d
2347d9: lea rdx, [rbp + 7]
2347dd: mov rcx, rdi
2347e0: call 0x29e190
2347e5: test eax, eax
2347e7: je 0x23487a
2347ed: mov r9d, dword ptr [rbp - 0x25]
2347f1: xor esi, esi
2347f3: mov r8d, dword ptr [rbp - 0x29]
2347f7: mov rcx, rdi
2347fa: mov rdx, qword ptr [rbx + 0x1b8]
234801: mov dword ptr [rsp + 0x28], esi
234805: mov dword ptr [rsp + 0x20], r15d
23480a: call 0x29e260
23480f: mov r8d, dword ptr [rbp - 0x35]
234813: lea rax, [rbp + 0x17]
234817: mov edx, dword ptr [rbp - 0x39]
23481a: xor r9d, r9d
23481d: mov dword ptr [rsp + 0x38], r15d
234822: mov rcx, rdi
234825: mov byte ptr [rsp + 0x30], sil
23482a: mov qword ptr [rsp + 0x28], rax
23482f: lea rax, [rbp - 0x29]
234833: mov qword ptr [rsp + 0x20], rax
234838: call 0x29e4c0
23483d: lea r9, [rbp - 9]
234841: mov qword ptr [rbp - 9], rsi
234845: xor r8d, r8d
234848: mov edx, r15d
23484b: mov rcx, rdi
23484e: call 0x29ea40
234853: mov eax, dword ptr [rbp - 0x25]
234856: lea rdx, [rbp + 7]
23485a: mov r9d, dword ptr [rbp - 0x35]
23485e: mov rcx, rdi
234861: mov r8d, dword ptr [rbp - 0x39]
234865: mov dword ptr [rsp + 0x30], r15d
23486a: mov dword ptr [rsp + 0x28], eax
23486e: mov eax, dword ptr [rbp - 0x29]
234871: mov dword ptr [rsp + 0x20], eax
234875: call 0x29df60
23487a: movzx ecx, byte ptr [rip + 0x38c333] ; b'\n'
234881: lea rdx, [rbx + 0xc]
234885: movzx r8d, byte ptr [rbx + 0x28]
23488a: movzx edi, r12b
23488e: inc edi
234890: mov eax, edi
234892: imul eax, dword ptr [rbx + 0xd4]
234899: add eax, dword ptr [rbx + 0xcc]
23489f: sar eax, cl
2348a1: mov rcx, qword ptr [rbx + 0x18]
2348a5: mov dword ptr [rbp - 0x39], eax
2348a8: call 0x180c10
2348ad: mov ecx, dword ptr [rbx + 0xd8]
2348b3: mov r9d, eax
2348b6: imul ecx, edi
2348b9: add ecx, dword ptr [rbx + 0xd0]
2348bf: lea eax, [rcx + rcx*2]
2348c2: movzx ecx, byte ptr [rip + 0x38c2eb] ; b'\n'
2348c9: cdq 
2348ca: and edx, 3
2348cd: add eax, edx
2348cf: sar eax, 2
2348d2: sar eax, cl
2348d4: sub eax, dword ptr [rbx + 0x14]
2348d7: add r9d, eax
2348da: mov eax, dword ptr [rbx + 0x3bc]
2348e0: mov dword ptr [rbp - 0x35], r9d
2348e4: test eax, eax
2348e6: jle 0x234994
2348ec: lea rdx, [rbp - 0x31]
2348f0: mov dword ptr [rbp - 0x31], eax
2348f3: lea rcx, [rbp - 0x2d]
2348f7: mov dword ptr [rbp - 0x2d], edi
2348fa: call 0x407bc0
2348ff: mov r9d, dword ptr [rbp - 0x35]
234903: sub r9d, eax
234906: jmp 0x2349b2
23490b: movzx ecx, byte ptr [rip + 0x38c2a2] ; b'\n'
234912: lea rdx, [rbx + 0xc]
234916: movzx r8d, byte ptr [rbx + 0x28]
23491b: movzx edi, r12b
23491f: inc edi
234921: mov eax, edi
234923: imul eax, dword ptr [rbx + 0xd4]
23492a: add eax, dword ptr [rbx + 0xcc]
234930: sar eax, cl
234932: mov rcx, r13
234935: mov dword ptr [rbp - 0x39], eax
234938: call 0x180c10
23493d: movzx ecx, byte ptr [rip + 0x38c270] ; b'\n'
234944: mov r9d, eax
234947: mov eax, dword ptr [rbx + 0xd8]
23494d: imul eax, edi
234950: add eax, dword ptr [rbx + 0xd0]
234956: lea eax, [rax + rax*2]
234959: cdq 
23495a: and edx, 3
23495d: add eax, edx
23495f: sar eax, 2
234962: sar eax, cl
234964: sub eax, dword ptr [rbx + 0x14]
234967: add r9d, eax
23496a: mov eax, dword ptr [rbx + 0x3bc]
234970: mov dword ptr [rbp - 0x35], r9d
234974: test eax, eax
234976: jle 0x234994
234978: lea rdx, [rbp - 0x2d]
23497c: mov dword ptr [rbp - 0x2d], eax
23497f: lea rcx, [rbp - 0x31]
234983: mov dword ptr [rbp - 0x31], edi
234986: call 0x407bc0
23498b: mov r9d, dword ptr [rbp - 0x35]
23498f: sub r9d, eax
234992: jmp 0x2349b2
234994: jns 0x2349b6
234996: neg eax
234998: mov dword ptr [rbp - 0x31], edi
23499b: lea rdx, [rbp - 0x2d]
23499f: mov dword ptr [rbp - 0x2d], eax
2349a2: lea rcx, [rbp - 0x31]
2349a6: call 0x407bc0
2349ab: mov r9d, dword ptr [rbp - 0x35]
2349af: add r9d, eax
2349b2: mov dword ptr [rbp - 0x35], r9d
2349b6: inc r12b
2349b9: cmp r12b, byte ptr [rbx + 0x3b8]
2349c0: jae 0x2349d6
2349c2: mov r10d, dword ptr [rbp + 0x13]
2349c6: mov r11d, dword ptr [rbp + 0xf]
2349ca: mov esi, dword ptr [rbp + 0xb]
2349cd: mov r14d, dword ptr [rbp + 7]
2349d1: jmp 0x234670
2349d6: mov r13, qword ptr [rsp + 0xc0]
2349de: mov rdi, qword ptr [rsp + 0xf0]
2349e6: mov r12, qword ptr [rsp + 0xf8]
2349ee: mov r14, qword ptr [rsp + 0xb8]
2349f6: mov rsi, qword ptr [rsp + 0xe8]
2349fe: mov r15, qword ptr [rsp + 0xb0]
234a06: mov rcx, qword ptr [rbp + 0x27]
234a0a: xor rcx, rsp
234a0d: call 0x4f77a0
234a12: add rsp, 0xc8
234a19: pop rbx
234a1a: pop rbp
234a1b: ret 
234a1c: int3 
234a1d: int3 
234a1e: int3 
234a1f: int3 
234a20: mov r11, rsp
234a23: push rbp
234a24: push rdi
234a25: lea rbp, [r11 - 0x5f]
234a29: sub rsp, 0xc8
234a30: mov rax, qword ptr [rip + 0x42ffa1] ; b'2\xa2\xdf-\x99+'
234a37: xor rax, rsp
234a3a: mov qword ptr [rbp + 0x27], rax
234a3e: mov r9, qword ptr [rcx + 0x18]
234a42: mov rdi, rcx
234a45: test r9, r9
234a48: je 0x234f32
234a4e: movsx ecx, word ptr [rcx + 0x216]
234a55: lea rax, [r9 + 0x5c8]
234a5c: mov qword ptr [r11 + 0x10], rbx
234a60: xor ebx, ebx
234a62: mov qword ptr [r11 + 0x20], r12
234a66: mov qword ptr [rbp - 1], rax
234a6a: movzx eax, byte ptr [rip + 0x378422] ; b'\x08'
234a71: cmp ecx, eax
234a73: mov qword ptr [r11 - 0x20], r14
234a77: mov qword ptr [r11 - 0x28], r15
234a7b: cmovg ebx, dword ptr [rip + 0x36d8ca] ; b'\x10'
234a82: cmp word ptr [rdi + 0x214], 5
234a8a: jne 0x234aa8
234a8c: movzx eax, byte ptr [rip + 0x3783fc] ; b'\x04'
234a93: cmp ecx, eax
234a95: jle 0x234aa8
234a97: movzx eax, byte ptr [rip + 0x3783f9] ; b'\x0c\xff\xff\x0e\x01\xe8\x03\x03\x05\x10'
234a9e: cmp ecx, eax
234aa0: jge 0x234aa8
234aa2: or ebx, dword ptr [rip + 0x36d8a8] ; b' '
234aa8: mov ecx, dword ptr [r9 + 0x688]
234aaf: mov edx, dword ptr [r9 + 0x68c]
234ab6: mov eax, dword ptr [r9 + 0x648]
234abd: sub eax, dword ptr [r9 + 0x640]
234ac4: movzx r8d, byte ptr [rdi + 0x28]
234ac9: add eax, ecx
234acb: mov dword ptr [rbp - 0x21], eax
234ace: mov eax, dword ptr [r9 + 0x64c]
234ad5: sub eax, dword ptr [r9 + 0x644]
234adc: add eax, edx
234ade: mov dword ptr [rbp - 0x1d], ecx
234ae1: mov dword ptr [rbp - 0x19], eax
234ae4: mov rcx, r9
234ae7: mov eax, dword ptr [rdi + 0xc]
234aea: mov dword ptr [rbp - 0x15], edx
234aed: lea rdx, [rdi + 0xc]
234af1: mov dword ptr [rbp - 0x39], eax
234af4: call 0x180c10
234af9: mov ecx, dword ptr [rdi + 0x10]
234afc: lea rdx, [rbp - 0x29]
234b00: sub ecx, dword ptr [rdi + 0x14]
234b03: add eax, ecx
234b05: mov rcx, qword ptr [rdi + 0x1b8]
234b0c: mov dword ptr [rbp - 0x35], eax
234b0f: call 0x411660
234b14: mov rcx, qword ptr [rdi + 0x1b8]
234b1b: lea rdx, [rbp - 0x11]
234b1f: call 0x411780
234b24: mov r11d, dword ptr [rbp - 0x11]
234b28: xor r15d, r15d
234b2b: mov r10d, dword ptr [rbp - 0xd]
234b2f: xor r14d, r14d
234b32: xor r12b, r12b
234b35: mov qword ptr [rbp + 7], r15
234b39: mov dword ptr [rbp + 0xf], r11d
234b3d: mov dword ptr [rbp + 0x13], r10d
234b41: cmp byte ptr [rdi + 0x3b9], r12b
234b48: jbe 0x234f12
234b4e: mov r9d, dword ptr [rbp - 0x35]
234b52: mov qword ptr [rsp + 0xf0], rsi
234b5a: mov qword ptr [rsp + 0xc0], r13
234b62: nop dword ptr [rax]
234b66: nop word ptr [rax + rax]
234b70: movzx ecx, byte ptr [rip + 0x36a074] ; b' \x0f'
234b77: mov eax, r9d
234b7a: mov r13, qword ptr [rdi + 0x18]
234b7e: cdq 
234b7f: mov esi, dword ptr [rbp - 0x39]
234b82: idiv ecx
234b84: movsx ecx, word ptr [r13 + 0xbbc]
234b8c: movsx r8d, ax
234b90: mov eax, esi
234b92: imul r8d, ecx
234b96: cdq 
234b97: movzx ecx, byte ptr [rip + 0x36a04c] ; b'  \x0f'
234b9e: idiv ecx
234ba0: add ax, r8w
234ba4: movsx rax, ax
234ba8: test eax, eax
234baa: js 0x234e36
234bb0: cmp eax, dword ptr [r13 + 0xbb8]
234bb7: jge 0x234e36
234bbd: mov rcx, rax
234bc0: mov rax, qword ptr [r13 + 0xbb0]
234bc7: movzx ecx, word ptr [rax + rcx*2]
234bcb: test word ptr [rip + 0x36a016], cx ; b'\xff\x7f  \x0f'
234bd2: je 0x234e36
234bd8: movsx ecx, word ptr [rdi + 0x216]
234bdf: movzx eax, byte ptr [rip + 0x3782ad] ; b'\x08'
234be6: cmp ecx, eax
234be8: jle 0x234bf9
234bea: mov r8d, r15d
234bed: sub r8d, r11d
234bf0: add r8d, dword ptr [rbp - 0x29]
234bf4: add r8d, esi
234bf7: jmp 0x234c00
234bf9: mov r8d, esi
234bfc: sub r8d, dword ptr [rbp - 0x29]
234c00: cmp word ptr [rdi + 0x214], 5
234c08: mov dword ptr [rbp + 0x17], r8d
234c0c: jne 0x234c32
234c0e: movzx eax, byte ptr [rip + 0x37827a] ; b'\x04'
234c15: cmp ecx, eax
234c17: jle 0x234c32
234c19: movzx eax, byte ptr [rip + 0x378277] ; b'\x0c\xff\xff\x0e\x01\xe8\x03\x03\x05\x10'
234c20: cmp ecx, eax
234c22: jge 0x234c32
234c24: mov edx, r14d
234c27: sub edx, r10d
234c2a: add edx, dword ptr [rbp - 0x25]
234c2d: add edx, r9d
234c30: jmp 0x234c38
234c32: mov edx, r9d
234c35: sub edx, dword ptr [rbp - 0x25]
234c38: mov esi, dword ptr [rbp - 0x21]
234c3b: sub r11d, r15d
234c3e: sub r10d, r14d
234c41: mov dword ptr [rbp + 0x1b], edx
234c44: add r10d, edx
234c47: mov dword ptr [rbp + 0x23], r10d
234c4b: lea r9d, [r11 + r8]
234c4f: mov dword ptr [rbp + 0x1f], r9d
234c53: cmp r8d, esi
234c56: jge 0x234e36
234c5c: mov eax, dword ptr [rbp - 0x1d]
234c5f: cmp r9d, eax
234c62: jl 0x234e36
234c68: mov r11d, dword ptr [rbp - 0x19]
234c6c: cmp edx, r11d
234c6f: jge 0x234e36
234c75: mov r14d, dword ptr [rbp - 0x15]
234c79: cmp r10d, r14d
234c7c: jl 0x234e36
234c82: cmp r8d, eax
234c85: mov ecx, eax
234c87: mov eax, esi
234c89: cmovge ecx, r8d
234c8d: cmp esi, r9d
234c90: mov r8d, r14d
234c93: cmovge eax, r9d
234c97: cmp edx, r14d
234c9a: cmovge r8d, edx
234c9e: cmp r11d, r10d
234ca1: mov edx, r11d
234ca4: cmovge edx, r10d
234ca8: cmp eax, ecx
234caa: jle 0x234e36
234cb0: cmp edx, r8d
234cb3: jle 0x234e36
234cb9: cmp byte ptr [rdi + 0x3c0], 0
234cc0: je 0x234cd7
234cc2: or ebx, dword ptr [rip + 0x36d67c] ; b'\x80'
234cc8: mov eax, dword ptr [rip + 0x36d67a] ; b''
234cce: or ebx, 8
234cd1: not eax
234cd3: and ebx, eax
234cd5: jmp 0x234ce3
234cd7: or ebx, dword ptr [rip + 0x36d66b] ; b''
234cdd: and ebx, 0xfffffff7
234ce0: or ebx, 1
234ce3: mov rsi, qword ptr [rbp - 1]
234ce7: lea rax, [rbp - 0x29]
234ceb: mov rcx, rsi
234cee: mov qword ptr [rsp + 0x20], rax
234cf3: lea r9, [rbp - 0x39]
234cf7: mov r8d, ebx
234cfa: lea rdx, [rbp + 7]
234cfe: .byte 0xe8
234cff: lodsd eax, dword ptr [rsi]
