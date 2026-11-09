2270e0: mov qword ptr [rsp + 0x18], rbx
2270e5: push rbp
2270e6: push rsi
2270e7: push rdi
2270e8: push r12
2270ea: push r13
2270ec: push r14
2270ee: push r15
2270f0: mov rbp, rsp
2270f3: sub rsp, 0x30
2270f7: mov rax, qword ptr [rip + 0x43d8da] ; b'2\xa2\xdf-\x99+'
2270fe: xor rax, rsp
227101: mov qword ptr [rbp - 8], rax
227105: mov rdi, rdx
227108: mov rbx, rcx
22710b: call 0x226630
227110: lea rax, [rip + 0x374151] ; b'\xd0\x81"@\x01'
227117: mov qword ptr [rbx], rax
22711a: lea rcx, [rbx + 0x1c8]
227121: movzx edx, word ptr [rip + 0x399554] ; b'\x01'
227128: call 0x421010
22712d: lea rcx, [rbx + 0x220]
227134: call 0x410d80
227139: lea rcx, [rbx + 0x354]
227140: call 0x3ff870
227145: lea rcx, [rbx + 0x35c]
22714c: call 0x3ff870
227151: lea rcx, [rbx + 0x364]
227158: call 0x3ff870
22715d: xor r9d, r9d
227160: mov dword ptr [rbx + 0x3b0], 0xa
22716a: mov dword ptr [rbx + 0x398], r9d
227171: lea rax, [rip + 0x3740e8] ; b'\x80\x80"@\x01'
227178: mov qword ptr [rbx + 0x380], rax
22717f: mov eax, r9d
227182: mov qword ptr [rbx + 0x3a0], r9
227189: mov qword ptr [rbx + 0x390], r9
227190: mov qword ptr [rbx + 0x388], r9
227197: mov qword ptr [rbx + 0x3a8], r9
22719e: mov r8d, dword ptr [rbx + 0x188]
2271a5: mov qword ptr [rbp - 0x10], r9
2271a9: mov qword ptr [rbp - 0x10], r9
2271ad: mov qword ptr [rbp - 0x10], r9
2271b1: mov qword ptr [rbp - 0x10], r9
2271b5: mov qword ptr [rbp - 0x10], r9
2271b9: mov qword ptr [rbp - 0x10], r9
2271bd: mov qword ptr [rbx + 0xcc], rax
2271c4: mov qword ptr [rbx + 0xd4], rax
2271cb: mov qword ptr [rbx + 0xf8], rax
2271d2: mov qword ptr [rbx + 0xdc], rax
2271d9: mov qword ptr [rbx + 0xe4], rax
2271e0: mov qword ptr [rbx + 0xec], rax
2271e7: mov qword ptr [rbx + 0x68], r9
2271eb: mov word ptr [rbx + 0x15a], r9w
2271f3: bt r8d, 0x15
2271f8: jae 0x22722d
2271fa: movzx ecx, byte ptr [rip + 0x3999b3] ; b'\n'
227201: movsx edx, word ptr [rbx + 0x64]
227205: shl edx, cl
227207: mov dword ptr [rbp - 0x10], edx
22720a: mov dword ptr [rbp - 0xc], edx
22720d: neg edx
22720f: mov rax, qword ptr [rbp - 0x10]
227213: add edx, edx
227215: mov dword ptr [rbp - 0x10], edx
227218: mov dword ptr [rbp - 0xc], edx
22721b: mov qword ptr [rbx + 0xec], rax
227222: mov rax, qword ptr [rbp - 0x10]
227226: mov qword ptr [rbx + 0xe4], rax
22722d: mov eax, r8d
227230: lea rsi, [rdi + 0xfc]
227237: shr eax, 0x1d
22723a: lea rdx, [rip + 0x3c456c] ; b''
227241: and al, 1
227243: mov ecx, 0x7fff
227248: mov byte ptr [rbx + 0x341], al
22724e: bt r8d, 0x11
227253: mov eax, 0x32
227258: cmovae ax, cx
22725c: mov rcx, rsi
22725f: mov word ptr [rbx + 0x184], ax
227266: mov dword ptr [rbx + 0x21c], 1
227270: mov word ptr [rbx + 0x216], r9w
227278: mov dword ptr [rbx + 0x118], 0x20000
227282: movups xmm0, xmmword ptr [rip + 0x369777] ; b'\xff\x05\x05\x05\x05\x05\x05\x05\x05\x05\xff\x05\x05\xff\x05\x05'
227289: movups xmmword ptr [rbx + 0x100], xmm0
227290: call 0x3ffb60
227295: mov ecx, 0x138
22729a: test eax, eax
22729c: je 0x2273c2
2272a2: call 0x4f7a88
2272a7: test rax, rax
2272aa: je 0x2272b7
2272ac: mov rdx, qword ptr [rsi]
2272af: mov rcx, rax
2272b2: call 0x410e10
2272b7: mov qword ptr [rbx + 0x1b8], rax
2272be: mov rcx, rax
2272c1: movzx edx, byte ptr [rdi + 0x10c]
2272c8: call 0x412380
2272cd: mov byte ptr [rbx + 0x340], 0
2272d4: test byte ptr [rdi + 0xf8], 1
2272db: je 0x227383
2272e1: mov rcx, qword ptr [rbx + 0x1b8]
2272e8: lea rdx, [rbx + 0x1c8]
2272ef: call 0x412390
2272f4: xor sil, sil
2272f7: lea r14, [rdi + 0x11c]
2272fe: nop 
227300: mov rax, qword ptr [rip + 0x440241] ; b''
227307: lea rcx, [rbx + 0x1c8]
22730e: movzx r8d, byte ptr [r14]
227312: movzx edx, sil
227316: mov r9, qword ptr [rax + 0x1090]
22731d: add r9, 0x63d8
227324: call 0x4221c0
227329: inc sil
22732c: lea r14, [r14 + 1]
227330: cmp sil, 7
227334: jb 0x227300
227336: xor esi, esi
227338: mov qword ptr [rbx + 0x1c0], rsi
22733f: mov dword ptr [rbx + 0x210], esi
227345: test byte ptr [rdi + 0xf8], 0x20
22734c: je 0x227427
227352: mov ecx, 0x138
227357: mov dword ptr [rbx + 0x210], 1
227361: call 0x4f7a88
227366: test rax, rax
227369: je 0x22740e
22736f: mov rdx, qword ptr [rdi + 0x104]
227376: mov rcx, rax
227379: call 0x410e10
22737e: jmp 0x227411
227383: lea rdx, [rip + 0x3c4423] ; b''
22738a: lea rcx, [rdi + 0x114]
227391: call 0x3ffb60
227396: test eax, eax
227398: je 0x227336
22739a: mov r9d, 1
2273a0: mov byte ptr [rbx + 0x340], 1
2273a7: mov r8d, r9d
2273aa: lea rdx, [rdi + 0x114]
2273b1: lea rcx, [rbx + 0x220]
2273b8: call 0x18aa40
2273bd: jmp 0x227336
2273c2: call 0x4f7a88
2273c7: mov rsi, rax
2273ca: test rax, rax
2273cd: je 0x2273ee
2273cf: lea rdx, [rip + 0x375662] ; b'SPMAGMIS'
2273d6: lea rcx, [rbp - 0x10]
2273da: call 0x3ff7c0
2273df: mov rcx, rsi
2273e2: mov rdx, qword ptr [rax]
2273e5: call 0x410e10
2273ea: xor esi, esi
2273ec: jmp 0x2273f2
2273ee: xor esi, esi
2273f0: mov eax, esi
2273f2: xor edx, edx
2273f4: mov qword ptr [rbx + 0x1b8], rax
2273fb: mov rcx, rax
2273fe: call 0x412380
227403: mov dword ptr [rbx + 0x21c], esi
227409: jmp 0x227338
22740e: mov rax, rsi
227411: mov qword ptr [rbx + 0x1c0], rax
227418: mov rcx, rax
22741b: movzx edx, byte ptr [rdi + 0x10d]
227422: call 0x412380
227427: mov dword ptr [rbx + 0x344], esi
22742d: test byte ptr [rdi + 0xf8], 2
227434: je 0x227489
227436: mov dword ptr [rbx + 0x344], 1
227440: mov byte ptr [rbx + 0x350], 0
227447: movzx eax, byte ptr [rdi + 0x123]
22744e: mov byte ptr [rbx + 0x348], al
227454: movzx eax, word ptr [rdi + 0x12c]
22745b: mov word ptr [rbx + 0x352], ax
227462: mov eax, dword ptr [rdi + 0x124]
227468: mov dword ptr [rbx + 0x349], eax
22746e: movzx eax, word ptr [rdi + 0x128]
227475: mov word ptr [rbx + 0x34d], ax
22747c: movzx eax, byte ptr [rdi + 0x12a]
227483: mov byte ptr [rbx + 0x34f], al
227489: mov dword ptr [rbx + 0x200], esi
22748f: mov eax, dword ptr [rdi + 0xf8]
227495: test al, 0x40
227497: je 0x2274d1
227499: mov dword ptr [rbx + 0x200], 1
2274a3: movsx eax, word ptr [rdi + 0x110]
2274aa: mov dword ptr [rbx + 0x204], eax
2274b0: movsx eax, word ptr [rdi + 0x112]
2274b7: mov dword ptr [rbx + 0x208], eax
2274bd: movzx eax, word ptr [rdi + 0x10e]
2274c4: mov word ptr [rbx + 0x20c], ax
2274cb: mov eax, dword ptr [rdi + 0xf8]
2274d1: shr eax, 3
2274d4: and eax, 1
2274d7: mov dword ptr [rbx + 0x1f8], eax
2274dd: mov eax, dword ptr [rdi + 0xf8]
2274e3: shr eax, 4
2274e6: and eax, 1
2274e9: mov dword ptr [rbx + 0x1fc], eax
2274ef: mov eax, dword ptr [rdi + 0xf8]
2274f5: test al, al
2274f7: jns 0x227506
2274f9: or dword ptr [rbx + 0x118], 8
227500: mov eax, dword ptr [rdi + 0xf8]
227506: bt eax, 9
22750a: jae 0x227516
22750c: or dword ptr [rbx + 0x118], 0x200
227516: movzx eax, byte ptr [rdi + 0x12b]
22751d: lea r8, [rdi + 0x12e]
227524: lea rdx, [rbp - 0x10]
227528: mov word ptr [rbx + 0x214], ax
22752f: lea rcx, [rbx + 0x354]
227536: call 0x3ff880
22753b: lea r8, [rdi + 0x136]
227542: lea rdx, [rbp - 0x10]
227546: lea rcx, [rbx + 0x35c]
22754d: call 0x3ff880
227552: lea r8, [rdi + 0x13e]
227559: lea rdx, [rbp - 0x10]
22755d: lea rcx, [rbx + 0x364]
227564: call 0x3ff880
227569: movzx eax, word ptr [rdi + 0x146]
227570: mov word ptr [rbx + 0x36c], ax
227577: movzx eax, word ptr [rdi + 0x148]
22757e: mov word ptr [rbx + 0x36e], ax
227585: movzx eax, word ptr [rdi + 0x14a]
22758c: mov word ptr [rbx + 0x370], ax
227593: mov eax, dword ptr [rdi + 0x14c]
227599: mov dword ptr [rbx + 0x374], eax
22759f: mov dword ptr [rbx + 0x378], esi
2275a5: mov rcx, qword ptr [rbx + 0x3a8]
2275ac: mov dword ptr [rbx + 0x398], esi
2275b2: mov qword ptr [rbx + 0x3a0], rsi
2275b9: mov qword ptr [rbx + 0x390], rsi
2275c0: mov qword ptr [rbx + 0x388], rsi
2275c7: call 0x407b40
2275cc: mov rax, rbx
2275cf: mov qword ptr [rbx + 0x3a8], rsi
2275d6: mov rcx, qword ptr [rbp - 8]
2275da: xor rcx, rsp
2275dd: call 0x4f77a0
2275e2: mov rbx, qword ptr [rsp + 0x80]
2275ea: add rsp, 0x30
2275ee: pop r15
2275f0: pop r14
2275f2: pop r13
2275f4: pop r12
2275f6: pop rdi
2275f7: pop rsi
2275f8: pop rbp
2275f9: ret 
