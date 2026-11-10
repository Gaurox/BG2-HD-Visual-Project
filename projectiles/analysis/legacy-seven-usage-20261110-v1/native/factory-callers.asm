14c9f2: xor ebx, ebx
14c9f4: mov eax, dword ptr [rsp + 0x78]
14c9f8: mov rdx, r15
14c9fb: mov dword ptr [rbx + 0x10], eax
14c9fe: mov eax, dword ptr [rsp + 0x88]
14ca05: mov dword ptr [rbx + 0x18], eax
14ca08: mov eax, dword ptr [rsp + 0x90]
14ca0f: mov dword ptr [rbx + 0x1c], eax
14ca12: mov dword ptr [rbx], r13d
14ca15: mov dword ptr [rbx + 4], r12d
14ca19: mov dword ptr [rbx + 0x14], ebp
14ca1c: movzx ecx, word ptr [rdi + 0xa0]
14ca23: inc cx
14ca26: call 0x22bf00
14ca2b: mov qword ptr [rbx + 8], rax
14ca2f: test rax, rax
14ca32: je 0x14ca43
14ca34: mov dword ptr [rax + 0x6c], esi

16a50b: mov qword ptr [rsp + 0x78], rbx
16a510: mov eax, 0xffff
16a515: mov ecx, 1
16a51a: mov qword ptr [rsp + 0x70], rdi
16a51f: mov qword ptr [rsp + 0x68], r14
16a524: cmp word ptr [rsi + 0xe], ax
16a528: je 0x16a52e
16a52a: movzx ecx, word ptr [rsi + 0x2a]
16a52e: mov rdx, rbp
16a531: call 0x22bf00
16a536: xor ebx, ebx
16a538: mov r14, rax
16a53b: mov edi, ebx
16a53d: cmp bx, word ptr [rsi + 0x1e]

16a8e0: mov qword ptr [rsp + 0x70], rbx
16a8e5: mov eax, 0xffff
16a8ea: mov ecx, 1
16a8ef: mov qword ptr [rsp + 0x78], rdi
16a8f4: mov qword ptr [rsp + 0x80], r14
16a8fc: cmp word ptr [rbp + 0xe], ax
16a900: je 0x16a906
16a902: movzx ecx, word ptr [rbp + 0x2a]
16a906: mov rdx, rsi
16a909: call 0x22bf00
16a90e: xor ebx, ebx
16a910: mov r14, rax
16a913: mov edi, ebx
16a915: cmp bx, word ptr [rbp + 0x1e]

16aef2: mov dword ptr [rdi + 0x18], r15d
16aef6: mov dword ptr [rdi + 0x1c], 0xbed7d7
16aefd: mov dword ptr [rdi + 0x20], 0xffffffff
16af04: mov byte ptr [rdi + 0x24], 0
16af08: mov word ptr [rdi + 0x2c], 0x100
16af0e: jmp 0x16af13
16af10: mov rdi, rax
16af13: mov rcx, qword ptr [rip + 0x4fc62e]
16af1a: xor r8d, r8d
16af1d: add rcx, 0x1768
16af24: mov rdx, rdi
16af27: call 0x204ec0
16af2c: jmp 0x16addf
16af31: movzx ecx, word ptr [rdi + 0x26]
16af35: test r12, r12
16af38: je 0x16af46
16af3a: movzx eax, word ptr [r12]
16af3f: test ax, ax
16af42: cmovne cx, ax
16af46: mov rdx, r14
16af49: call 0x22bf00
16af4e: mov r13, rax
16af51: test r12, r12
16af54: je 0x16af99
16af56: movsx ecx, word ptr [rax + 0x64]

16bcc4: mov dword ptr [rdi + 0x1c], 0xbed7d7
16bccb: mov dword ptr [rdi + 0x20], 0xffffffff
16bcd2: mov byte ptr [rdi + 0x24], 0
16bcd6: mov dword ptr [rdi + 0x28], 0
16bcdd: mov word ptr [rdi + 0x2c], 0x100
16bce3: jmp 0x16bce7
16bce5: xor edi, edi
16bce7: mov rcx, qword ptr [rip + 0x4fb85a]
16bcee: xor r8d, r8d
16bcf1: add rcx, 0x1768
16bcf8: mov rdx, rdi
16bcfb: call 0x204ec0
16bd00: jmp 0x16bbbd
16bd05: movzx ecx, word ptr [r13 + 0x26]
16bd0a: test rsi, rsi
16bd0d: je 0x16bd19
16bd0f: movzx eax, word ptr [rsi]
16bd12: test ax, ax
16bd15: cmovne cx, ax
16bd19: mov rdx, r14
16bd1c: call 0x22bf00
16bd21: mov qword ptr [rsp + 0x50], rax
16bd26: mov rbx, rax
16bd29: test rsi, rsi
16bd2c: je 0x16bd6c

16c97a: mov rdx, rax
16c97d: test rax, rax
16c980: je 0x16c997
16c982: mov eax, dword ptr [rbx + 0x48]
16c985: mov dword ptr [rdx + 0xc], eax
16c988: mov dword ptr [rdx + 8], eax
16c98b: lea rax, [rip + 0x423a7e]
16c992: mov qword ptr [rdx], rax
16c995: jmp 0x16c99a
16c997: mov rdx, rax
16c99a: mov rcx, qword ptr [rip + 0x4faba7]
16c9a1: xor r8d, r8d
16c9a4: add rcx, 0x1768
16c9ab: call 0x204ec0
16c9b0: cmp byte ptr [r13 + 0xc], 3
16c9b5: mov edi, 1
16c9ba: movzx ecx, di
16c9bd: je 0x16c9c4
16c9bf: movzx ecx, word ptr [r13 + 0x26]
16c9c4: mov rdx, rbx
16c9c7: call 0x22bf00
16c9cc: mov rdx, qword ptr [rbx]
16c9cf: mov rcx, rbx
16c9d2: mov r14, rax
16c9d5: call qword ptr [rdx + 8]

16df1d: lea rcx, [rsp + 0x50]
16df22: call 0x3fd740
16df27: mov dword ptr [rsp + 0x30], r12d
16df2c: lea rcx, [rbx + 0x49b0]
16df33: mov edx, 0x12b
16df38: mov dword ptr [rsp + 0x28], r12d
16df3d: lea r9d, [r12 + 1]
16df42: mov dword ptr [rsp + 0x20], r12d
16df47: lea r8d, [r12 - 1]
16df4c: call 0x1e5480
16df51: mov dword ptr [rsp + 0x30], r12d
16df56: lea rcx, [rbx + 0x4a00]
16df5d: mov edx, 0x12b
16df62: mov dword ptr [rsp + 0x28], r12d
16df67: lea r9d, [r12 + 1]
16df6c: mov dword ptr [rsp + 0x20], r12d
16df71: lea r8d, [r12 - 1]
16df76: call 0x1e5480
16df7b: movzx ecx, word ptr [r14 + 0x26]
16df80: mov rdx, rbx
16df83: call 0x22bf00
16df88: mov r12, rax
16df8b: xor eax, eax
16df8d: mov esi, eax
16df8f: cmp ax, word ptr [r14 + 0x1e]

1a8c0a: jmp rcx
1a8c0c: mov edi, 0x6e
1a8c11: jmp 0x1a8c49
1a8c13: mov edi, 0x6f
1a8c18: jmp 0x1a8c49
1a8c1a: mov edi, 0x70
1a8c1f: jmp 0x1a8c49
1a8c21: mov edi, 0x71
1a8c26: jmp 0x1a8c49
1a8c28: mov edi, 0x72
1a8c2d: jmp 0x1a8c49
1a8c2f: mov edi, 0x73
1a8c34: jmp 0x1a8c49
1a8c36: mov edi, 0x74
1a8c3b: jmp 0x1a8c49
1a8c3d: mov edi, 0x75
1a8c42: jmp 0x1a8c49
1a8c44: movzx edi, word ptr [r15 + 0x1c]
1a8c49: lea ecx, [rdi + 1]
1a8c4c: mov rdx, rbp
1a8c4f: call 0x22bf00
1a8c54: mov r14, rax
1a8c57: mov word ptr [rax + 0x184], bx
1a8c5e: mov eax, dword ptr [rbp + 0x1120]
1a8c64: bt eax, 0x10

1a8eaa: call 0x3fff70
1a8eaf: mov rdi, qword ptr [rsp + 0xd8]
1a8eb7: mov rcx, rsi
1a8eba: mov rax, qword ptr [rsi]
1a8ebd: movsxd rbx, dword ptr [rdi - 8]
1a8ec1: call qword ptr [rax + 0x20]
1a8ec4: mov rdx, rax
1a8ec7: lea rcx, [rsp + 0xd0]
1a8ecf: call 0x3fd640
1a8ed4: mov rcx, qword ptr [rsp + 0xd0]
1a8edc: mov r8, rbx
1a8edf: mov rdx, rdi
1a8ee2: call 0x5161e0
1a8ee7: lea rcx, [rsp + 0xd0]
1a8eef: mov ebx, eax
1a8ef1: call 0x3fd740
1a8ef6: test ebx, ebx
1a8ef8: jne 0x1a9022
1a8efe: movzx ecx, word ptr [rbp + 0x20]
1a8f02: mov rdx, r15
1a8f05: call 0x22bf00
1a8f0a: mov ecx, 0x28
1a8f0f: mov rbx, rax
1a8f12: call 0x4f7a88
1a8f17: test rax, rax

1caaed: mov qword ptr [rsp + 0x88], rdi
1caaf5: mov qword ptr [rsp + 0x50], r12
1caafa: mov qword ptr [rsp + 0x40], r15
1caaff: je 0x1cab10
1cab01: mov rax, qword ptr [rcx + 0x88]
1cab08: mov r15d, 0xffffffff
1cab0e: jmp 0x1cab18
1cab10: mov rax, qword ptr [rdx + 0xc]
1cab14: mov r15d, dword ptr [rdx + 0x48]
1cab18: movzx edi, word ptr [rcx + 0x20]
1cab1c: mov qword ptr [rsp + 0x78], rax
1cab21: shr rax, 0x20
1cab25: inc eax
1cab27: mov dword ptr [rsp + 0x7c], eax
1cab2b: mov eax, 0xfff
1cab30: and di, ax
1cab33: mov eax, 0x1000
1cab38: add di, ax
1cab3b: lea ecx, [rdi + 1]
1cab3e: call 0x22bf00
1cab43: mov r12, rax
1cab46: test rax, rax
1cab49: je 0x1cac0f

1cbf70: mov qword ptr [r11 - 0x30], rbx
1cbf74: lea rdx, [rip + 0x41f832]
1cbf7b: mov qword ptr [r11 - 0x38], rdi
1cbf7f: mov r13, r9
1cbf82: mov r15, r8
1cbf85: mov rsi, rcx
1cbf88: call 0x3ffa80
1cbf8d: test eax, eax
1cbf8f: je 0x1cc035
1cbf95: mov ecx, 0x90
1cbf9a: mov rdx, r15
1cbf9d: call 0x22bf00
1cbfa2: mov ecx, 0x28
1cbfa7: mov rsi, rax
1cbfaa: call 0x4f7a88
1cbfaf: xor edi, edi

1e46cb: test r14w, r14w
1e46cf: lea ebx, [r14 - 1]
1e46d3: cmove bx, r14w
1e46d8: test r13, r13
1e46db: jne 0x1e4706
1e46dd: cmp qword ptr [rdi], r13
1e46e0: je 0x1e46fe
1e46e2: lea rcx, [rdi + 8]
1e46e6: lea rdx, [rip + 0x4070c0]
1e46ed: call 0x3ffb60
1e46f2: test eax, eax
1e46f4: je 0x1e46fe
1e46f6: mov rcx, qword ptr [rdi]
1e46f9: call 0x1e1e0
1e46fe: mov qword ptr [rdi], r15
1e4701: jmp 0x1e4bf0
1e4706: movzx ecx, word ptr [r13 + 0x26]
1e470b: test cx, cx
1e470e: je 0x1e471b
1e4710: mov rdx, rsi
1e4713: call 0x22bf00
1e4718: mov r15, rax
1e471b: xor eax, eax
1e471d: mov r14d, eax
1e4720: cmp ax, word ptr [r13 + 0x1e]

212d41: call 0x276700
212d46: test al, al
212d48: jne 0x212dc2
212d4a: mov rdx, qword ptr [rip + 0x45480f]
212d51: cmp byte ptr [rdx + 0x2c9], 1
212d58: jne 0x212dc2
212d5a: mov rcx, qword ptr [rsp + 0x58]
212d5f: mov eax, dword ptr [rcx + 0x50]
212d62: cmp dword ptr [rdx + 0x374], eax
212d68: je 0x212dc2
212d6a: cmp qword ptr [rcx + 0x18], 0
212d6f: je 0x212dc2
212d71: mov rax, qword ptr [rcx]
212d74: call qword ptr [rax + 8]
212d77: movzx ecx, word ptr [rbx + 0x10]
212d7b: and al, 1
212d7d: je 0x212d86
212d7f: mov rdx, qword ptr [rsp + 0x58]
212d84: jmp 0x212d88
212d86: xor edx, edx
212d88: call 0x22bf00
212d8d: mov rdx, qword ptr [rsp + 0x58]
212d92: mov rcx, rax
212d95: mov r9d, dword ptr [rbx + 0x14]
212d99: mov r10, qword ptr [rax]

229002: mov rdx, rax
229005: call 0x4075c0
22900a: test rdi, rdi
22900d: jne 0x228fe0
22900f: movzx eax, word ptr [rbx + 0x3f4]
229016: mov rcx, qword ptr [rbx + 0x3c8]
22901d: mov r9d, dword ptr [rbx + 0x6c]
229021: mov r8d, dword ptr [rbx + 0x68]
229025: mov rdx, qword ptr [rbx + 0x18]
229029: mov word ptr [rsp + 0x30], ax
22902e: mov eax, dword ptr [rbx + 0x3f0]
229034: mov dword ptr [rsp + 0x28], eax
229038: mov rax, qword ptr [rbx + 0xf8]
22903f: mov dword ptr [rbx + 0x3d0], 0
229049: mov r10, qword ptr [rcx]
22904c: mov qword ptr [rsp + 0x20], rax
229051: call qword ptr [r10 + 0xd0]
229058: movzx ecx, word ptr [rbx + 0x3c0]
22905f: xor edx, edx
229061: inc cx
229064: call 0x22bf00
229069: dec word ptr [rbx + 0x3b8]
229070: mov rdi, qword ptr [rsp + 0x60]
229075: mov qword ptr [rbx + 0x3c8], rax
22907c: movzx eax, word ptr [rbx + 0x3ba]

2293f0: mov qword ptr [rsp + 0xe8], rbp
2293f8: mov qword ptr [rsp + 0xc0], r13
229400: mov rbp, qword ptr [r14 + 0x10]
229404: lea rdx, [rsp + 0x50]
229409: mov r14, qword ptr [r14]
22940c: mov ecx, ebp
22940e: call 0x276700
229413: test al, al
229415: jne 0x2294f5
22941b: mov rcx, qword ptr [rsp + 0x50]
229420: mov rax, qword ptr [rcx]
229423: call qword ptr [rax + 8]
229426: test byte ptr [rip + 0x3702ed], al
22942c: je 0x2294f5
229432: mov r13, qword ptr [rsp + 0x50]
229437: mov ecx, 1
22943c: xor edx, edx
22943e: call 0x22bf00
229443: lea rdx, [rip + 0x3c2363]
22944a: mov rsi, rax
22944d: lea rcx, [rsp + 0x90]
229455: call 0x3ff7c0

22bdc0: mov qword ptr [rsp + 0x20], rbp
22bdc5: push rsi
22bdc6: push rdi
22bdc7: push r14
22bdc9: sub rsp, 0x40
22bdcd: mov rax, qword ptr [rip + 0x438c04]
22bdd4: xor rax, rsp
22bdd7: mov qword ptr [rsp + 0x30], rax
22bddc: mov r14, rcx
22bddf: mov rbp, rdx
22bde2: movzx ecx, word ptr [rcx + 0x3c4]
22bde9: xor edx, edx
22bdeb: inc cx
22bdee: call 0x22bf00
22bdf3: lea rdx, [rip + 0x3bf9b3]
22bdfa: mov rsi, rax
22bdfd: lea rcx, [rsp + 0x20]
22be02: call 0x3ff7c0

22c4be: or dword ptr [rbx + 0x118], 8
22c4c5: cmp di, r14w
22c4c9: jne 0x22c505
22c4cb: mov rax, qword ptr [rip + 0x43b076]
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
22c527: lea rdx, [rip + 0x3bf27f]

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
22c766: lea rdx, [rip + 0x3bf040]
22c76d: mov qword ptr [rbx + 0x3c8], rax
22c774: lea rcx, [rbx + 0x178]
22c77b: mov dword ptr [rbx + 0x70], 0xffffffff

22ebb1: call 0x2270e0
22ebb6: lea rax, [rip + 0x36d2fb]
22ebbd: mov edx, 0xa
22ebc2: lea rcx, [rbx + 0x3b8]
22ebc9: mov qword ptr [rbx], rax
22ebcc: call 0x4073a0
22ebd1: cmp qword ptr [rsp + 0x68], 0
22ebd7: lea rax, [rip + 0x35e17a]
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

22f76b: mov dword ptr [rbp - 0xd], r8d
22f76f: idiv ecx
22f771: mov rcx, qword ptr [rbx + 0x18]
22f775: lea r8, [rbx + 0x100]
22f77c: add rcx, 0xa60
22f783: mov dword ptr [rbp - 5], eax
22f786: lea rdx, [rbp - 9]
22f78a: call 0x24c8f0
22f78f: cmp al, byte ptr [rip + 0x36b86d]
22f795: je 0x22f7a2
22f797: mov rax, qword ptr [rbp - 0x11]
22f79b: mov qword ptr [rbx + 0xf8], rax
22f7a2: cmp dword ptr [rbx + 0x444], r14d
22f7a9: jbe 0x22f7b2
22f7ab: mov dword ptr [rbx + 0x3c8], r14d
22f7b2: cmp dword ptr [rbx + 0x3f4], r14d
22f7b9: je 0x22f8e4
22f7bf: movzx ecx, word ptr [rbx + 0x3f8]
22f7c6: xor edx, edx
22f7c8: inc cx
22f7cb: call 0x22bf00
22f7d0: lea rcx, [rip + 0x42bcb1]
22f7d7: mov rsi, rax
22f7da: mov dword ptr [rax + 0x1b0], 1
22f7e4: mov edx, dword ptr [rbx + 0x6c]

23074a: mov dword ptr [rsp + 0x20], 0
230752: call 0x40e180
230757: mov rcx, qword ptr [rdi + 0x3c8]
23075e: mov r9d, r13d
230761: mov eax, dword ptr [rdi + 0x48]
230764: mov r8d, r12d
230767: mov rdx, qword ptr [rsp + 0x40]
23076c: mov dword ptr [rcx + 0x70], eax
23076f: mov rcx, qword ptr [rdi + 0x3c8]
230776: movzx eax, word ptr [rsp + 0xe0]
23077e: mov word ptr [rsp + 0x30], ax
230783: mov dword ptr [rdi + 0x3f0], r15d
23078a: mov dword ptr [rdi + 0x3d0], 0
230794: mov r10, qword ptr [rcx]
230797: mov dword ptr [rsp + 0x28], r15d
23079c: mov qword ptr [rsp + 0x20], rbx
2307a1: call qword ptr [r10 + 0xd0]
2307a8: movzx ecx, word ptr [rdi + 0x3c0]
2307af: xor edx, edx
2307b1: inc cx
2307b4: call 0x22bf00
2307b9: dec word ptr [rdi + 0x3b8]
2307c0: mov r15, qword ptr [rsp + 0x68]
2307c5: mov qword ptr [rdi + 0x3c8], rax
2307cc: movzx eax, word ptr [rdi + 0x3ba]

37d507: mov r8d, esi
37d50a: lea rdx, [rsp + 0x20]
37d50f: mov rcx, rdi
37d512: call 0x39cc30
37d517: cmp qword ptr [rsp + 0x20], 0
37d51d: movsx esi, ax
37d520: je 0x37d541
37d522: lea rdx, [rip + 0x26e284]
37d529: lea rcx, [rsp + 0x28]
37d52e: call 0x3ffb60
37d533: test eax, eax
37d535: je 0x37d541
37d537: mov rcx, qword ptr [rsp + 0x20]
37d53c: call 0x1e1e0
37d541: mov r8d, esi
37d544: mov rdx, rbx
37d547: mov rcx, rdi
37d54a: call 0x353e90
37d54f: mov ecx, eax
37d551: mov rdx, rdi
37d554: call 0x22bf00
37d559: mov rsi, qword ptr [rsp + 0x60]
37d55e: mov rbx, rax
37d561: test rax, rax
37d564: je 0x37d593

3b5606: mov dword ptr [rsp + 0x28], r14d
3b560b: lea rcx, [rbx + 0x49b0]
3b5612: mov dword ptr [rsp + 0x20], r14d
3b5617: mov r9d, edi
3b561a: lea r8d, [rdi - 2]
3b561e: call 0x1e5480
3b5623: mov dword ptr [rsp + 0x30], r14d
3b5628: lea rcx, [rbx + 0x4a00]
3b562f: mov edx, 0x12b
3b5634: mov dword ptr [rsp + 0x28], r14d
3b5639: mov r9d, edi
3b563c: mov dword ptr [rsp + 0x20], r14d
3b5641: lea r8d, [rdi - 2]
3b5645: call 0x1e5480
3b564a: mov eax, 0xffff
3b564f: cmp word ptr [r13 + 0xe], ax
3b5654: je 0x3b565b
3b5656: movzx eax, word ptr [r13 + 0x26]
3b565b: mov rdx, rbx
3b565e: movzx ecx, ax
3b5661: call 0x22bf00
3b5666: mov qword ptr [rbx + 0x4ad8], rax
3b566d: xor eax, eax
3b566f: cmp ax, word ptr [r13 + 0x1e]
3b5674: jae 0x3b5986

3b722a: lea rcx, [rbp - 0x48]
3b722e: call 0x3fd740
3b7233: mov dword ptr [rsp + 0x30], r15d
3b7238: lea rcx, [rbx + 0x49b0]
3b723f: mov edx, 0x12b
3b7244: mov dword ptr [rsp + 0x28], r15d
3b7249: mov r9d, r14d
3b724c: mov dword ptr [rsp + 0x20], r15d
3b7251: mov r8d, 0xffffffff
3b7257: call 0x1e5480
3b725c: mov dword ptr [rsp + 0x30], r15d
3b7261: lea rcx, [rbx + 0x4a00]
3b7268: mov edx, 0x12b
3b726d: mov dword ptr [rsp + 0x28], r15d
3b7272: mov r9d, r14d
3b7275: mov dword ptr [rsp + 0x20], r15d
3b727a: mov r8d, 0xffffffff
3b7280: call 0x1e5480
3b7285: movzx ecx, word ptr [r13 + 0x26]
3b728a: mov rdx, rbx
3b728d: call 0x22bf00
3b7292: mov qword ptr [rbx + 0x4ad8], rax
3b7299: mov r14d, r15d
3b729c: cmp r15w, word ptr [r13 + 0x1e]
3b72a1: jae 0x3b74da

3b89cb: jns 0x3b89d7
3b89cd: mov word ptr [rbx + 0x4b4c], r14w
3b89d5: jmp 0x3b89e9
3b89d7: cmp ax, 0xa
3b89db: jle 0x3b89e9
3b89dd: mov eax, 0xa
3b89e2: mov word ptr [rbx + 0x4b4c], ax
3b89e9: mov byte ptr [rbx + 0x4ba8], r14b
3b89f0: mov dword ptr [rbx + 0x4bac], r14d
3b89f7: cmp byte ptr [r13], 2
3b89fc: jne 0x3b8a2f
3b89fe: mov rcx, qword ptr [rbx + 0x4ad8]
3b8a05: test rcx, rcx
3b8a08: je 0x3b8a1b
3b8a0a: mov rax, qword ptr [rcx]
3b8a0d: mov edx, 1
3b8a12: call qword ptr [rax]
3b8a14: mov qword ptr [rbx + 0x4ad8], r14
3b8a1b: movzx ecx, word ptr [r13 + 0x2a]
3b8a20: mov rdx, rbx
3b8a23: call 0x22bf00
3b8a28: mov qword ptr [rbx + 0x4ad8], rax
3b8a2f: cmp dword ptr [rbx + 0x4ea4], r14d
3b8a36: mov edi, 0x1132
3b8a3b: mov eax, edi

3b8f8e: call 0x204ec0
3b8f93: mov rcx, qword ptr [rbx + 0x4ad8]
3b8f9a: mov rdx, rbx
3b8f9d: mov rdi, rcx
3b8fa0: mov rsi, qword ptr [rcx]
3b8fa3: call 0x22f340
3b8fa8: movzx edx, word ptr [rip + 0x1e1f21]
3b8faf: mov rcx, rdi
3b8fb2: mov r9d, dword ptr [r15 + 0x48]
3b8fb6: mov r8d, dword ptr [rbx + 0x48]
3b8fba: mov word ptr [rsp + 0x30], dx
3b8fbf: mov rdx, qword ptr [rbx + 0x18]
3b8fc3: mov dword ptr [rsp + 0x28], eax
3b8fc7: mov rax, qword ptr [r13]
3b8fcb: mov qword ptr [rsp + 0x20], rax
3b8fd0: call qword ptr [rsi + 0xd0]
3b8fd6: mov r13, qword ptr [rsp + 0x68]
3b8fdb: mov rdx, rbx
3b8fde: mov qword ptr [rbx + 0x4ad8], r14
3b8fe5: movzx ecx, word ptr [r13 + 0x2a]
3b8fea: call 0x22bf00
3b8fef: mov qword ptr [rbx + 0x4ad8], rax
3b8ff6: mov r12, qword ptr [rsp + 0x58]
3b8ffb: movzx eax, byte ptr [rbx + 0x4ba8]
3b9002: mov esi, dword ptr [rsp + 0x50]

3b9086: call 0x38c810
3b908b: test eax, eax
3b908d: je 0x3b90a0
3b908f: mov rax, qword ptr [rbx]
3b9092: mov edx, 1
3b9097: mov rcx, rbx
3b909a: call qword ptr [rax + 0x160]
3b90a0: movzx edi, word ptr [rip + 0x1d64d1]
3b90a7: mov ecx, 0x50
3b90ac: call 0x4f7a88
3b90b1: test rax, rax
3b90b4: je 0x3b9a24
3b90ba: mov r9d, dword ptr [r15 + 0x48]
3b90be: lea rdx, [rbp]
3b90c2: mov r8d, dword ptr [rbx + 0x48]
3b90c6: mov rcx, rax
3b90c9: call 0x164df0
3b90ce: jmp 0x3b9a27
3b90d3: movzx ecx, word ptr [r13 + 0x2a]
3b90d8: mov rdx, rbx
3b90db: call 0x22bf00
3b90e0: mov qword ptr [rbx + 0x4ad8], rax
3b90e7: test rax, rax
3b90ea: je 0x3b8ff6
3b90f0: jmp 0x3b8d41

3bba13: mov rcx, qword ptr [rbx + r14*8 + 0xfc0]
3bba1b: mov qword ptr [rbx + 0x4ae8], rcx
3bba22: mov word ptr [rbx + 0x4af0], si
3bba29: test rcx, rcx
3bba2c: je 0x3bb0ac
3bba32: call 0x1fae60
3bba37: mov edx, dword ptr [rbx + 0x44c]
3bba3d: mov rcx, qword ptr [rbx + 0x4ae8]
3bba44: call 0x1fb330
3bba49: mov r13, rax
3bba4c: movzx eax, word ptr [rbx + 0x44c]
3bba53: mov word ptr [rbx + 0x4af2], ax
3bba5a: test r13, r13
3bba5d: je 0x3bb0ac
3bba63: mov esi, 1
3bba68: cmp dword ptr [rbp - 0x79], 0xffff
3bba6f: movzx ecx, si
3bba72: je 0x3bba79
3bba74: movzx ecx, word ptr [r13 + 0x2a]
3bba79: mov rdx, rbx
3bba7c: call 0x22bf00
3bba81: mov qword ptr [rbx + 0x4ad8], rax
3bba88: mov esi, r15d
3bba8b: cmp r15w, word ptr [r13 + 0x1e]
3bba90: jae 0x3bbcf6

3bc59a: jne 0x3bc5ad
3bc59c: cmp word ptr [rbx + 0x4990], -1
3bc5a4: je 0x3bc5b7
3bc5a6: mov dword ptr [rbx + 0x4994], r13d
3bc5ad: cmp word ptr [rbx + 0x4990], -1
3bc5b5: jne 0x3bc5c9
3bc5b7: mov word ptr [rbx + 0x4990], r13w
3bc5bf: mov dword ptr [rbx + 0x4994], 1
3bc5c9: cmp ax, 0x14
3bc5cd: jl 0x3bcaaa
3bc5d3: cmp dword ptr [rbx + 0x4994], r13d
3bc5da: je 0x3bcaaa
3bc5e0: test dword ptr [r14 + 0x26], 0x600
3bc5e8: je 0x3bc5fa
3bc5ea: mov rcx, rbx
3bc5ed: call 0x39c510
3bc5f2: mov rcx, rbx
3bc5f5: call 0x3b0480
3bc5fa: movzx ecx, word ptr [r14 + 0x2a]
3bc5ff: mov rdx, rbx
3bc602: call 0x22bf00
3bc607: mov qword ptr [rbx + 0x4ad8], rax
3bc60e: mov esi, r13d
3bc611: cmp r13w, word ptr [r14 + 0x1e]
3bc616: jae 0x3bc7eb
