SLOT 0 RVA 315e90
315e90: mov qword ptr [rsp + 8], rbx
315e95: push rdi
315e96: sub rsp, 0x20
315e9a: mov rdi, rcx
315e9d: mov ebx, edx
315e9f: add rcx, 0xf58
315ea6: call 0x140421100
315eab: lea rcx, [rdi + 0xe20]
315eb2: call 0x140411200
315eb7: lea rcx, [rdi + 0xce8]
315ebe: call 0x140411200
315ec3: mov rcx, rdi
315ec6: call 0x140315770
315ecb: test bl, 1
315ece: je 0x140315edd
315ed0: mov edx, 0xf98
315ed5: mov rcx, rdi
315ed8: call 0x14045e690
315edd: mov rbx, qword ptr [rsp + 0x30]
315ee2: mov rax, rdi
315ee5: add rsp, 0x20
315ee9: pop rdi
315eea: ret 

SLOT 1 RVA 316ab0
316ab0: mov qword ptr [rsp + 0x18], rbx
316ab5: push rsi
316ab6: push rdi
316ab7: push r14
316ab9: sub rsp, 0x30
316abd: mov r14, rdx
316ac0: mov rdi, rcx
316ac3: mov rcx, qword ptr [rcx + 0xcd0]
316aca: mov rdx, r8
316acd: mov rsi, r8
316ad0: call 0x140411660
316ad5: mov rcx, qword ptr [rdi + 0xcd0]
316adc: lea rdx, [rsp + 0x50]
316ae1: call 0x140411780
316ae6: xor eax, eax
316ae8: mov rcx, rdi
316aeb: mov qword ptr [r14], rax
316aee: mov eax, dword ptr [rsp + 0x50]
316af2: mov dword ptr [r14 + 8], eax
316af6: mov eax, dword ptr [rsp + 0x54]
316afa: mov dword ptr [r14 + 0xc], eax
316afe: mov rax, qword ptr [rdi]
316b01: call qword ptr [rax + 0x170]
316b07: test eax, eax
316b09: jne 0x140316b28
316b0b: mov rcx, qword ptr [rdi + 0xcd0]
316b12: test rcx, rcx
316b15: je 0x140316b28
316b17: lea rdx, [rsp + 0x58]
316b1c: call 0x140411780
316b21: mov eax, dword ptr [rsp + 0x5c]
316b25: mov dword ptr [rdi + 0x1c], eax
316b28: cmp byte ptr [rdi + 0x20], 0
316b2c: mov eax, 2
316b31: mov ebx, 8
316b36: mov rcx, r14
316b39: cmove ebx, eax
316b3c: xor r8d, r8d
316b3f: mov r9d, ebx
316b42: mov dword ptr [rsp + 0x20], ebx
316b46: xor edx, edx
316b48: call 0x140407b70
316b4d: shr ebx, 1
316b4f: add dword ptr [rsi], ebx
316b51: add dword ptr [rsi + 4], ebx
316b54: mov rbx, qword ptr [rsp + 0x60]
316b59: add rsp, 0x30
316b5d: pop r14
316b5f: pop rdi
316b60: pop rsi
316b61: ret 

SLOT 2 RVA 317ec0
317ec0: cmp dword ptr [rip + 0x3f7e51], 0
317ec7: mov r10, rdx
317eca: mov r11d, dword ptr [rsp + 0x30]
317ecf: je 0x140317eec
317ed1: movzx eax, byte ptr [rcx + 0xf94]
317ed8: cmp word ptr [rcx + 0xf8a], ax
317edf: jle 0x140317eec
317ee1: mov eax, dword ptr [r8]
317ee4: sub eax, r11d
317ee7: add eax, dword ptr [r9]
317eea: jmp 0x140317ef2
317eec: mov eax, dword ptr [r8]
317eef: sub eax, dword ptr [r9]
317ef2: mov dword ptr [rdx], eax
317ef4: mov edx, dword ptr [r8 + 4]
317ef8: sub edx, dword ptr [r9 + 4]
317efc: add edx, dword ptr [rsp + 0x28]
317f00: mov ecx, dword ptr [r10]
317f03: add ecx, r11d
317f06: mov dword ptr [r10 + 4], edx
317f0a: mov dword ptr [r10 + 8], ecx
317f0e: mov ecx, dword ptr [rsp + 0x38]
317f12: add ecx, edx
317f14: mov dword ptr [r10 + 0xc], ecx
317f18: ret 

SLOT 3 RVA 318630
318630: mov word ptr [rcx + 0xf8a], dx
318637: cmp dword ptr [rip + 0x3f76da], 0
31863e: jne 0x140318657
318640: movzx r8d, byte ptr [rcx + 0xf94]
318648: cmp dx, r8w
31864c: jle 0x140318657
31864e: mov r8, qword ptr [rcx + 0xce0]
318655: jmp 0x14031865e
318657: mov r8, qword ptr [rcx + 0xcd8]
31865e: mov qword ptr [rcx + 0xcd0], r8
318665: cmp dword ptr [rip + 0x3f76ac], 0
31866c: je 0x1403186b3
31866e: movsx edx, word ptr [rcx + 0xf8a]
318675: movzx eax, byte ptr [rcx + 0xf94]
31867c: cmp edx, eax
31867e: jle 0x1403186b3
318680: mov eax, 0xf
318685: sub eax, edx
318687: and eax, 0x8000000f
31868c: jge 0x140318695
31868e: dec eax
318690: or eax, 0xfffffff0
318693: inc eax
318695: movzx ecx, word ptr [rcx + 0xf88]
31869c: cdq 
31869d: sub eax, edx
31869f: shl cx, 3
3186a3: sar eax, 1
3186a5: add ax, cx
3186a8: mov rcx, r8
3186ab: movzx edx, ax
3186ae: jmp 0x140412380
3186b3: movsx eax, word ptr [rcx + 0xf8a]
3186ba: cdq 
3186bb: sub eax, edx
3186bd: movzx edx, word ptr [rcx + 0xf88]
3186c4: shl dx, 3
3186c8: mov rcx, r8
3186cb: sar eax, 1
3186cd: add ax, dx
3186d0: movzx edx, ax
3186d3: jmp 0x140412380
3186d8: int3 
3186d9: int3 
3186da: int3 
3186db: int3 
3186dc: int3 
3186dd: int3 
3186de: int3 
3186df: int3 
3186e0: mov qword ptr [rsp + 8], rbx
3186e5: push rdi
3186e6: sub rsp, 0x20
3186ea: mov rax, qword ptr [rcx + 0xd00]
3186f1: movzx r10d, dx
3186f5: mov rbx, rcx
3186f8: movzx edi, word ptr [rax + 0x118]
3186ff: mov word ptr [rcx + 0x240a], dx
318706: movzx edx, word ptr [rbx + 0x2408]
31870d: mov rcx, qword ptr [rcx + 0xd08]
318714: movzx eax, dx
318717: shl ax, 3
31871b: add dx, ax
31871e: mov qword ptr [rbx + 0xd00], rcx
318725: movzx eax, byte ptr [rbx + 0x2425]
31872c: movzx r8d, dx
318730: sub r8w, r10w
318734: add dx, r10w
318738: add r8w, 0x10
31873d: cmp r10w, ax
318741: cmovg dx, r8w
318746: call 0x140412380
31874b: mov rcx, qword ptr [rbx + 0xd00]
318752: movzx edx, di
318755: call 0x140411610
31875a: cmp qword ptr [rbx + 0x1360], 0
318762: je 0x1403187c3
318764: movzx r9d, word ptr [rbx + 0x2408]
31876c: movzx r10d, word ptr [rbx + 0x240a]
318774: movzx eax, r9w
318778: mov rcx, qword ptr [rbx + 0x1368]
31877f: shl ax, 3
318783: add r9w, ax
318787: mov qword ptr [rbx + 0x1360], rcx
31878e: movzx eax, byte ptr [rbx + 0x2425]
318795: movzx r8d, r9w
318799: sub r8w, r10w
31879d: add r8w, 0x10
3187a2: cmp r10w, ax
3187a6: lea edx, [r9 + r10]
3187aa: cmovg dx, r8w
3187af: call 0x140412380
3187b4: mov rcx, qword ptr [rbx + 0x1360]
3187bb: movzx edx, di
3187be: call 0x140411610
3187c3: cmp qword ptr [rbx + 0x1888], 0
3187cb: je 0x14031882c
3187cd: movzx r9d, word ptr [rbx + 0x2408]
3187d5: movzx r10d, word ptr [rbx + 0x240a]
3187dd: movzx eax, r9w
3187e1: mov rcx, qword ptr [rbx + 0x1890]
3187e8: shl ax, 3
3187ec: add r9w, ax
3187f0: mov qword ptr [rbx + 0x1888], rcx
3187f7: movzx eax, byte ptr [rbx + 0x2425]
3187fe: movzx r8d, r9w
318802: sub r8w, r10w
318806: add r8w, 0x10
31880b: cmp r10w, ax
31880f: lea edx, [r9 + r10]
318813: cmovg dx, r8w
318818: call 0x140412380
31881d: mov rcx, qword ptr [rbx + 0x1888]
318824: movzx edx, di
318827: call 0x140411610
31882c: cmp qword ptr [rbx + 0x1db0], 0
318834: je 0x140318895
318836: movzx r9d, word ptr [rbx + 0x2408]
31883e: movzx r10d, word ptr [rbx + 0x240a]
318846: movzx eax, r9w
31884a: mov rcx, qword ptr [rbx + 0x1db8]
318851: shl ax, 3
318855: add r9w, ax
318859: mov qword ptr [rbx + 0x1db0], rcx
318860: movzx eax, byte ptr [rbx + 0x2425]
318867: movzx r8d, r9w
31886b: sub r8w, r10w
31886f: add r8w, 0x10
318874: cmp r10w, ax
318878: lea edx, [r9 + r10]
31887c: cmovg dx, r8w
318881: call 0x140412380
318886: mov rcx, qword ptr [rbx + 0x1db0]
31888d: movzx edx, di
318890: call 0x140411610
318895: mov rbx, qword ptr [rsp + 0x30]
31889a: add rsp, 0x20
31889e: pop rdi
31889f: ret 

SLOT 4 RVA 1e1e0
1e1e0: ret 0

SLOT 5 RVA 1e1e0
1e1e0: ret 0

SLOT 6 RVA 1e1e0
1e1e0: ret 0

SLOT 7 RVA 1e1e0
1e1e0: ret 0

SLOT 8 RVA 1e1f0
1e1f0: xor eax, eax
1e1f2: ret 

SLOT 9 RVA 326a70
326a70: push rbx
326a72: sub rsp, 0x20
326a76: mov rbx, rdx
326a79: add rcx, 0xdf8
326a80: lea rdx, [rsp + 0x30]
326a85: call 0x1403fff70
326a8a: mov rdx, rax
326a8d: mov rcx, rbx
326a90: call 0x1403fd770
326a95: lea rcx, [rsp + 0x30]
326a9a: call 0x1403fd740
326a9f: add rsp, 0x20
326aa3: pop rbx
326aa4: ret 

SLOT 10 RVA 255b0
255b0: mov al, 1
255b2: ret 

SLOT 11 RVA 255b0
255b0: mov al, 1
255b2: ret 

SLOT 12 RVA 327170
327170: movzx eax, word ptr [rcx + 0x5f2]
327177: ret 

SLOT 13 RVA 327310
327310: movzx eax, byte ptr [rcx + 0x21]
327314: ret 

SLOT 14 RVA 327320
327320: movzx eax, byte ptr [rcx + 0x22]
327324: ret 

SLOT 15 RVA 25960
25960: xor al, al
25962: ret 

SLOT 16 RVA 1e1e0
1e1e0: ret 0

SLOT 17 RVA 11dc40
11dc40: movzx eax, byte ptr [rcx + 0xb]
11dc44: ret 

SLOT 18 RVA 3373d0
3373d0: mov byte ptr [rcx + 0xb], dl
3373d3: ret 

SLOT 19 RVA 330d70
330d70: movzx eax, byte ptr [rcx + 0xa]
330d74: mov byte ptr [rcx + 0xb], al
330d77: ret 

SLOT 20 RVA 327a90
327a90: movzx eax, byte ptr [rcx + 0xa]
327a94: ret 

SLOT 21 RVA 327ac0
327ac0: movsx rax, r8w
327ac4: sar rax, 1
327ac7: mov eax, dword ptr [rcx + rax*4 + 0x30]
327acb: mov dword ptr [rdx], eax
327acd: mov rax, rdx
327ad0: ret 

SLOT 22 RVA 327a00
327a00: lea rax, [rcx + 0xc]
327a04: ret 

SLOT 23 RVA 1e1f0
1e1f0: xor eax, eax
1e1f2: ret 

SLOT 24 RVA 327b20
327b20: movzx eax, byte ptr [rcx + 0x5f0]
327b27: ret 

SLOT 25 RVA 327b30
327b30: lea rax, [rip + 0x2c3c76]
327b37: ret 

SLOT 26 RVA 327c20
327c20: mov rax, qword ptr [rcx + 0x28]
327c24: ret 

SLOT 27 RVA 327b30
327b30: lea rax, [rip + 0x2c3c76]
327b37: ret 

SLOT 28 RVA 327b30
327b30: lea rax, [rip + 0x2c3c76]
327b37: ret 

SLOT 29 RVA 329110
329110: mov eax, dword ptr [rcx + 0x24]
329113: ret 

SLOT 30 RVA 32a260
32a260: mov eax, dword ptr [rcx + 0xf8c]
32a266: ret 

SLOT 31 RVA 32a310
32a310: mov eax, dword ptr [rcx + 0xf90]
32a316: ret 

SLOT 32 RVA 32a380
32a380: cmp dword ptr [rip + 0x3e5991], 0
32a387: je 0x14032a39f
32a389: movzx eax, byte ptr [rcx + 0xf94]
32a390: cmp word ptr [rcx + 0xf8a], ax
32a397: jle 0x14032a39f
32a399: mov eax, 1
32a39e: ret 

SLOT 33 RVA 32a170
32a170: mov rdx, qword ptr [rcx + 0xcd0]
32a177: xor eax, eax
32a179: cmp word ptr [rdx + 0x118], ax
32a180: sete al
32a183: ret 

SLOT 34 RVA 32a1e0
32a1e0: mov rcx, qword ptr [rcx + 0xcd0]
32a1e7: jmp 0x140411df0
32a1ec: int3 
32a1ed: int3 
32a1ee: int3 
32a1ef: int3 
32a1f0: mov rcx, qword ptr [rcx + 0xd00]
32a1f7: jmp 0x140411df0
32a1fc: int3 
32a1fd: int3 
32a1fe: int3 
32a1ff: int3 
32a200: mov rcx, qword ptr [rcx + 0xcf8]
32a207: jmp 0x140411df0
32a20c: int3 
32a20d: int3 
32a20e: int3 
32a20f: int3 
32a210: mov rcx, qword ptr [rcx + 0xcd8]
32a217: jmp 0x140411eb0
32a21c: int3 
32a21d: int3 
32a21e: int3 
32a21f: int3 
32a220: mov rcx, qword ptr [rcx + 0xcd0]
32a227: jmp 0x140411eb0
32a22c: int3 
32a22d: int3 
32a22e: int3 
32a22f: int3 
32a230: mov rcx, qword ptr [rcx + 0xd00]
32a237: jmp 0x140411eb0
32a23c: int3 
32a23d: int3 
32a23e: int3 
32a23f: int3 
32a240: mov rcx, qword ptr [rcx + 0xcf8]
32a247: jmp 0x140411eb0
32a24c: int3 
32a24d: int3 
32a24e: int3 
32a24f: int3 
32a250: mov eax, dword ptr [rcx + 0xf94]
32a256: ret 

SLOT 35 RVA 32a220
32a220: mov rcx, qword ptr [rcx + 0xcd0]
32a227: jmp 0x140411eb0
32a22c: int3 
32a22d: int3 
32a22e: int3 
32a22f: int3 
32a230: mov rcx, qword ptr [rcx + 0xd00]
32a237: jmp 0x140411eb0
32a23c: int3 
32a23d: int3 
32a23e: int3 
32a23f: int3 
32a240: mov rcx, qword ptr [rcx + 0xcf8]
32a247: jmp 0x140411eb0
32a24c: int3 
32a24d: int3 
32a24e: int3 
32a24f: int3 
32a250: mov eax, dword ptr [rcx + 0xf94]
32a256: ret 

SLOT 36 RVA 3296e0
3296e0: mov rcx, qword ptr [rcx + 0xcd0]
3296e7: mov rax, qword ptr [rcx]
3296ea: jmp qword ptr [rax]
3296ed: int3 
3296ee: int3 
3296ef: int3 
3296f0: mov qword ptr [rsp + 8], rbx
3296f5: push rdi
3296f6: sub rsp, 0x20
3296fa: mov rbx, rcx
3296fd: mov rcx, qword ptr [rcx + 0xd00]
329704: mov rax, qword ptr [rcx]
329707: call qword ptr [rax]
329709: mov rax, qword ptr [rbx + 0xd00]
329710: mov rcx, qword ptr [rbx + 0x1360]
329717: movzx edi, word ptr [rax + 0x118]
32971e: test rcx, rcx
329721: je 0x14032972b
329723: movzx edx, di
329726: call 0x140411610
32972b: mov rcx, qword ptr [rbx + 0x1888]
329732: test rcx, rcx
329735: je 0x14032973f
329737: movzx edx, di
32973a: call 0x140411610
32973f: mov rcx, qword ptr [rbx + 0x1db0]
329746: test rcx, rcx
329749: je 0x140329753
32974b: movzx edx, di
32974e: call 0x140411610
329753: mov rbx, qword ptr [rsp + 0x30]
329758: add rsp, 0x20
32975c: pop rdi
32975d: ret 

SLOT 37 RVA 31e1a0
31e1a0: mov rax, qword ptr [rcx + 0xcd0]
31e1a7: dec word ptr [rax + 0x118]
31e1ae: ret 

SLOT 38 RVA 32be60
32be60: push rbp
32be62: push r12
32be64: push r13
32be66: push r14
32be68: push r15
32be6a: lea rbp, [rsp - 7]
32be6f: sub rsp, 0xd0
32be76: mov rax, qword ptr [rip + 0x338b5b]
32be7d: xor rax, rsp
32be80: mov qword ptr [rbp - 0x19], rax
32be84: mov rax, qword ptr [rbp + 0x57]
32be88: mov r14, rcx
32be8b: mov rcx, qword ptr [rbp + 0x77]
32be8f: mov r13, rdx
32be92: movups xmm0, xmmword ptr [r9]
32be96: mov r12, qword ptr [rbp + 0x5f]
32be9a: movzx edx, byte ptr [rbp + 0x97]
32bea1: mov qword ptr [rbp - 0x61], rcx
32bea5: mov rcx, qword ptr [rbp + 0x9f]
32beac: mov qword ptr [rbp - 0x59], rcx
32beb0: mov rcx, qword ptr [rax]
32beb3: mov qword ptr [rsp + 0x40], rcx
32beb8: shr rcx, 0x20
32bebc: add ecx, dword ptr [rbp + 0x8f]
32bec2: cmp dword ptr [rip + 0x3e3e4f], 0
32bec9: mov dword ptr [rsp + 0x44], ecx
32becd: mov ecx, dword ptr [rbp + 0x67]
32bed0: movaps xmmword ptr [rbp - 0x39], xmm0
32bed4: je 0x14032beff
32bed6: movzx eax, byte ptr [r14 + 0xf94]
32bede: cmp word ptr [r14 + 0xf8a], ax
32bee6: jle 0x14032beee
32bee8: or ecx, dword ptr [rip + 0x27645e]
32beee: test dl, dl
32bef0: jne 0x14032bf02
32bef2: mov eax, dword ptr [rip + 0x276450]
32bef8: or eax, 1
32befb: or ecx, eax
32befd: jmp 0x14032bf08
32beff: or ecx, 4
32bf02: or ecx, dword ptr [rip + 0x27643c]
32bf08: mov r15d, ecx
32bf0b: mov qword ptr [rsp + 0x20], r12
32bf10: or r15d, 2
32bf14: lea r9, [rsp + 0x40]
32bf19: test dl, dl
32bf1b: lea rdx, [rbp - 0x39]
32bf1f: cmove r15d, ecx
32bf23: mov rcx, r13
32bf26: mov r8d, r15d
32bf29: call 0x14029e1b0
32bf2e: mov r8d, r15d
32bf31: lea rdx, [rbp - 0x39]
32bf35: mov rcx, r13
32bf38: call 0x14029e190
32bf3d: test eax, eax
32bf3f: je 0x14032c221
32bf45: cmp dword ptr [r14 + 0xba8], 0
32bf4d: mov qword ptr [rsp + 0x110], rbx
32bf55: mov qword ptr [rsp + 0xc8], rsi
32bf5d: mov qword ptr [rsp + 0xc0], rdi
32bf65: je 0x14032bfa6
32bf67: mov rcx, qword ptr [r14 + 0xcb0]
32bf6e: call 0x1403f6d50
32bf73: mov rbx, qword ptr [r14 + 0xcb0]
32bf7a: mov rcx, rbx
32bf7d: call 0x1403f7890
32bf82: mov rcx, rbx
32bf85: mov edi, eax
32bf87: call 0x1403f78b0
32bf8c: movzx r9d, word ptr [rip + 0x2946e4]
32bf94: mov rdx, rax
32bf97: mov rcx, qword ptr [r14 + 0xcd0]
32bf9e: mov r8d, edi
32bfa1: call 0x1404123c0
32bfa6: mov rcx, qword ptr [r14 + 0xcd0]
32bfad: add rcx, 8
32bfb1: call 0x1403f7a10
32bfb6: mov r8d, dword ptr [rbp + 0x6f]
32bfba: mov esi, eax
32bfbc: movzx ecx, al
32bfbf: xor r9d, r9d
32bfc2: movzx edx, r8b
32bfc6: add edx, 0xffffff01
32bfcc: mov dword ptr [rsp + 0x48], r9d
32bfd1: add edx, ecx
32bfd3: mov dword ptr [rbp - 0x75], r9d
32bfd7: movzx ecx, ax
32bfda: mov dword ptr [rbp - 0x69], edx
32bfdd: shr ecx, 8
32bfe0: movzx edx, r8w
32bfe4: shr eax, 0x10
32bfe7: shr edx, 8
32bfea: add edx, 0xffffff01
32bff0: shr r8d, 0x10
32bff4: add ecx, edx
32bff6: mov dword ptr [rbp - 0x6d], r9d
32bffa: mov dword ptr [rbp - 0x79], ecx
32bffd: lea rdx, [rbp - 0x79]
32c001: movzx ecx, al
32c004: movzx eax, r8b
32c008: add eax, 0xffffff01
32c00d: add ecx, eax
32c00f: mov dword ptr [rbp - 0x71], ecx
32c012: lea rcx, [rbp - 0x75]
32c016: call 0x140407bb0
32c01b: movzx ebx, al
32c01e: lea rdx, [rbp - 0x71]
32c022: lea rcx, [rbp - 0x6d]
32c026: shl ebx, 8
32c029: call 0x140407bb0
32c02e: movzx edi, al
32c031: lea rdx, [rbp - 0x69]
32c035: shl edi, 0x10
32c038: lea rcx, [rsp + 0x48]
32c03d: or edi, ebx
32c03f: call 0x140407bb0
32c044: mov rcx, qword ptr [r14 + 0xcd0]
32c04b: movzx edx, al
32c04e: add rcx, 8
32c052: or edx, edi
32c054: call 0x140412690
32c059: movzx eax, byte ptr [rbp + 0x97]
32c060: mov rcx, r13
32c063: mov r9d, dword ptr [r12 + 4]
32c068: mov r8d, dword ptr [r12]
32c06c: mov rdx, qword ptr [r14 + 0xcd0]
32c073: mov dword ptr [rsp + 0x28], eax
32c077: mov dword ptr [rsp + 0x20], r15d
32c07c: call 0x14029e260
32c081: mov rcx, qword ptr [r14 + 0xcd0]
32c088: mov edx, esi
32c08a: add rcx, 8
32c08e: call 0x140412690
32c093: mov rdx, qword ptr [rbp - 0x61]
32c097: mov ecx, dword ptr [rbp + 0x8f]
32c09d: mov r9d, ecx
32c0a0: mov r8d, dword ptr [rsp + 0x44]
32c0a5: mov dword ptr [rsp + 0x38], r15d
32c0aa: mov eax, dword ptr [rdx]
32c0ac: mov dword ptr [rbp - 0x29], eax
32c0af: mov eax, dword ptr [rdx + 4]
32c0b2: sub eax, ecx
32c0b4: mov dword ptr [rbp - 0x25], eax
32c0b7: mov eax, dword ptr [rdx + 8]
32c0ba: mov dword ptr [rbp - 0x21], eax
32c0bd: mov eax, dword ptr [rdx + 0xc]
32c0c0: mov edx, dword ptr [rsp + 0x40]
32c0c4: sub eax, ecx
32c0c6: mov dword ptr [rbp - 0x1d], eax
32c0c9: sub r8d, ecx
32c0cc: movzx eax, byte ptr [rbp + 0x7f]
32c0d0: mov byte ptr [rsp + 0x30], al
32c0d4: lea rax, [rbp - 0x29]
32c0d8: mov qword ptr [rsp + 0x28], rax
32c0dd: mov qword ptr [rsp + 0x20], r12
32c0e2: mov rcx, r13
32c0e5: call 0x14029e4c0
32c0ea: cmp dword ptr [rbp + 0x87], 0
32c0f1: lea r9, [rsp + 0x48]
32c0f6: mov rdi, qword ptr [rsp + 0xc0]
32c0fe: mov edx, r15d
32c101: mov rsi, qword ptr [rsp + 0xc8]
32c109: mov rbx, qword ptr [rsp + 0x110]
32c111: je 0x14032c136
32c113: mov ecx, dword ptr [r12]
32c117: lea r8, [rbp - 0x39]
32c11b: add ecx, dword ptr [rsp + 0x40]
32c11f: mov rax, qword ptr [rsp + 0x40]
32c124: shr rax, 0x20
32c128: add eax, dword ptr [r12 + 4]
32c12d: mov dword ptr [rbp - 0x7d], eax
32c130: mov dword ptr [rsp + 0x48], ecx
32c134: jmp 0x14032c140
32c136: xor eax, eax
32c138: mov qword ptr [rsp + 0x48], rax
32c13d: xor r8d, r8d
32c140: mov rcx, r13
32c143: call 0x14029ea40
32c148: movaps xmm0, xmmword ptr [rbp - 0x39]
32c14c: lea rcx, [rbp - 0x49]
32c150: xor r8d, r8d
32c153: movdqa xmmword ptr [rbp - 0x49], xmm0
32c158: xor edx, edx
32c15a: cmp byte ptr [r14 + 0x20], dl
32c15e: je 0x14032c183

SLOT 39 RVA 319dc0
319dc0: test dl, 0xf0
319dc3: jne 0x140319e3a
319dc5: push rdi
319dc6: sub rsp, 0x20
319dca: cmp dword ptr [rcx + 0xf8c], 0
319dd1: mov rdi, rcx
319dd4: je 0x140319e3b
319dd6: and dl, 0xf
319dd9: mov qword ptr [rsp + 0x30], rbx
319dde: mov qword ptr [rsp + 0x38], rsi
319de3: add rcx, 0xce8
319dea: movzx esi, dl
319ded: movzx edx, si
319df0: call 0x1404114f0
319df5: movzx edx, si
319df8: lea rcx, [rdi + 0xce8]
319dff: call 0x1404126c0
319e04: cmp dword ptr [rip + 0x3f5f0d], 0
319e0b: jne 0x140319e2b
319e0d: movzx edx, si
319e10: lea rcx, [rdi + 0xe20]
319e17: call 0x1404114f0
319e1c: movzx edx, si
319e1f: lea rcx, [rdi + 0xe20]
319e26: call 0x1404126c0
319e2b: mov rbx, qword ptr [rsp + 0x30]
319e30: mov rsi, qword ptr [rsp + 0x38]
319e35: add rsp, 0x20
319e39: pop rdi
319e3a: ret 

SLOT 40 RVA 31ccf0
31ccf0: push rbx
31ccf2: sub rsp, 0x20
31ccf6: cmp dword ptr [rcx + 0xf8c], 0
31ccfd: mov rbx, rcx
31cd00: je 0x14031cd30
31cd02: mov qword ptr [rsp + 0x30], rdi
31cd07: xor dil, dil
31cd0a: nop word ptr [rax + rax]
31cd10: mov rax, qword ptr [rbx]
31cd13: movzx edx, dil
31cd17: mov rcx, rbx
31cd1a: call qword ptr [rax + 0x138]
31cd20: inc dil
31cd23: cmp dil, 7
31cd27: jb 0x14031cd10
31cd29: mov rdi, qword ptr [rsp + 0x30]
31cd2e: jmp 0x14031cd7b
31cd30: movzx ecx, byte ptr [rip + 0x2a3948]
31cd37: mov edx, ecx
31cd39: mov eax, ecx
31cd3b: shl edx, 8
31cd3e: shl eax, 0x10
31cd41: or edx, eax
31cd43: or edx, ecx
31cd45: lea rcx, [rbx + 0xcf0]
31cd4c: call 0x140412690
31cd51: cmp dword ptr [rip + 0x3f2fc0], 0
31cd58: jne 0x14031cd7b
31cd5a: movzx ecx, byte ptr [rip + 0x2a391e]
31cd61: mov edx, ecx
31cd63: mov eax, ecx
31cd65: shl edx, 8
31cd68: shl eax, 0x10
31cd6b: or edx, eax
31cd6d: or edx, ecx
31cd6f: lea rcx, [rbx + 0xe28]
31cd76: call 0x140412690
31cd7b: lea rcx, [rbx + 0xce8]
31cd82: call 0x140411570
31cd87: mov byte ptr [rbx + 0xdef], 0
31cd8e: cmp dword ptr [rip + 0x3f2f83], 0
31cd95: jne 0x14031cdaa
31cd97: lea rcx, [rbx + 0xe20]
31cd9e: call 0x140411570
31cda3: mov byte ptr [rbx + 0xf27], 0
31cdaa: add rsp, 0x20
31cdae: pop rbx
31cdaf: ret 

SLOT 41 RVA 3315c0
3315c0: test r8b, 0xf0
3315c4: jne 0x14033168c
3315ca: push rbx
3315cb: push rsi
3315cc: push rdi
3315cd: sub rsp, 0x30
3315d1: cmp dword ptr [rcx + 0xf8c], 0
3315d8: mov esi, r9d
3315db: mov qword ptr [rsp + 0x50], rbp
3315e0: movzx ebx, dl
3315e3: mov qword ptr [rsp + 0x60], r14
3315e8: mov rdi, rcx
3315eb: je 0x14033168d
3315f1: and r8b, 0xf
3315f5: mov qword ptr [rsp + 0x58], r12
3315fa: movzx r12d, byte ptr [rsp + 0x70]
331600: add rcx, 0xce8
331607: movzx ebp, r8b
33160b: mov qword ptr [rsp + 0x68], r15
331610: movzx r8d, bp
331614: movzx r15d, dl
331618: movzx edx, r15w
33161c: mov byte ptr [rsp + 0x20], r12b
331621: call 0x140411330
331626: test bl, bl
331628: je 0x140331639
33162a: movzx edx, bp
33162d: lea rcx, [rdi + 0xce8]
331634: call 0x1404126a0
331639: cmp dword ptr [rip + 0x3de6d8], 0
331640: jne 0x140331671
331642: mov r9d, esi
331645: mov byte ptr [rsp + 0x20], r12b
33164a: movzx r8d, bp
33164e: lea rcx, [rdi + 0xe20]
331655: movzx edx, r15w
331659: call 0x140411330
33165e: test bl, bl
331660: je 0x140331671
331662: movzx edx, bp
331665: lea rcx, [rdi + 0xe20]
33166c: call 0x1404126a0
331671: mov r12, qword ptr [rsp + 0x58]
331676: mov r15, qword ptr [rsp + 0x68]
33167b: mov rbp, qword ptr [rsp + 0x50]
331680: mov r14, qword ptr [rsp + 0x60]
331685: add rsp, 0x30
331689: pop rdi
33168a: pop rsi
33168b: pop rbx
33168c: ret 

SLOT 42 RVA 335000
335000: mov qword ptr [rsp + 8], rbx
335005: mov qword ptr [rsp + 0x10], rbp
33500a: mov qword ptr [rsp + 0x18], rsi
33500f: mov qword ptr [rsp + 0x20], rdi
335014: push r14
335016: sub rsp, 0x30
33501a: cmp dword ptr [rcx + 0xf8c], 0
335021: movzx r14d, r9b
335025: mov esi, r8d
335028: movzx ebp, dl
33502b: mov rdi, rcx
33502e: je 0x140335065
335030: xor bl, bl
335032: nop dword ptr [rax]
335036: nop word ptr [rax + rax]
335040: mov rax, qword ptr [rdi]
335043: mov r9d, esi
335046: movzx r8d, bl
33504a: mov byte ptr [rsp + 0x20], r14b
33504f: movzx edx, bpl
335053: mov rcx, rdi
335056: call qword ptr [rax + 0x148]
33505c: inc bl
33505e: cmp bl, 7
335061: jb 0x140335040
335063: jmp 0x1403350e3
335065: test bpl, bpl
335068: jne 0x140335091
33506a: add rcx, 0xcf0
335071: mov edx, esi
335073: call 0x140412690
335078: cmp dword ptr [rip + 0x3dac99], 0
33507f: jne 0x1403350e3
335081: lea rcx, [rdi + 0xe28]
335088: mov edx, esi
33508a: call 0x140412690
33508f: jmp 0x1403350e3
335091: movzx ebp, bpl
335095: movzx r9d, r14b
335099: movzx edx, bp
33509c: add rcx, 0xce8
3350a3: call 0x140411420
3350a8: xor edx, edx
3350aa: lea rcx, [rdi + 0xce8]
3350b1: call 0x1404126a0
3350b6: cmp dword ptr [rip + 0x3dac5b], 0
3350bd: jne 0x1403350e3
3350bf: movzx r9d, r14b
3350c3: lea rcx, [rdi + 0xe20]
3350ca: mov r8d, esi
3350cd: movzx edx, bp
3350d0: call 0x140411420
3350d5: xor edx, edx
3350d7: lea rcx, [rdi + 0xe20]
3350de: call 0x1404126a0
3350e3: mov rbx, qword ptr [rsp + 0x40]
3350e8: mov rbp, qword ptr [rsp + 0x48]
3350ed: mov rsi, qword ptr [rsp + 0x50]
3350f2: mov rdi, qword ptr [rsp + 0x58]
3350f7: add rsp, 0x30
3350fb: pop r14
3350fd: ret 

SLOT 43 RVA 336a00
336a00: cmp dword ptr [rcx + 0xf8c], 0
336a07: je 0x140336a39
336a09: test dl, 0xf0
336a0c: jne 0x140336a39
336a0e: mov rax, qword ptr [rip + 0x330b33]
336a15: and dl, 0xf
336a18: movzx r8d, r8b
336a1c: add rcx, 0xf58
336a23: movzx edx, dl
336a26: mov r9, qword ptr [rax + 0x1090]
336a2d: add r9, 0x63d8
336a34: jmp 0x1404221c0
336a39: ret 

SLOT 44 RVA 336e40
336e40: mov qword ptr [rsp + 0x10], rsi
336e45: push rdi
336e46: sub rsp, 0x20
336e4a: cmp dword ptr [rcx + 0xf8c], 0
336e51: movzx esi, dl
336e54: mov rdi, rcx
336e57: je 0x140336e7f
336e59: mov qword ptr [rsp + 0x30], rbx
336e5e: xor bl, bl
336e60: mov rax, qword ptr [rdi]
336e63: movzx r8d, sil
336e67: movzx edx, bl
336e6a: mov rcx, rdi
336e6d: call qword ptr [rax + 0x158]
336e73: inc bl
336e75: cmp bl, 7
336e78: jb 0x140336e60
336e7a: mov rbx, qword ptr [rsp + 0x30]
336e7f: mov rsi, qword ptr [rsp + 0x38]
336e84: add rsp, 0x20
336e88: pop rdi
336e89: ret 

SLOT 45 RVA 3376c0
3376c0: mov qword ptr [rsp + 8], rbx
3376c5: mov qword ptr [rsp + 0x10], rbp
3376ca: mov qword ptr [rsp + 0x18], rsi
3376cf: push rdi
3376d0: sub rsp, 0x20
3376d4: xor ebp, ebp
3376d6: movsx esi, dx
3376d9: mov rdi, rcx
3376dc: mov ebx, ebp
3376de: lea eax, [rsi - 1]
3376e1: cmp eax, 0xf
3376e4: ja 0x140337802
3376ea: lea rcx, [rip - 0x3376f1]
3376f1: cdqe 
3376f3: mov r8d, dword ptr [rcx + rax*4 + 0x33787c]
3376fb: add r8, rcx
3376fe: jmp r8
337701: lea rax, [rdi + 0xce8]
337708: mov qword ptr [rdi + 0xcd8], rax
33770f: lea rax, [rdi + 0xe20]
337716: mov qword ptr [rdi + 0xce0], rax
33771d: mov eax, 2
337722: jmp 0x1403377fb
337727: lea rax, [rdi + 0xce8]
33772e: mov qword ptr [rdi + 0xcd8], rax
337735: lea rax, [rdi + 0xe20]
33773c: mov qword ptr [rdi + 0xce0], rax
337743: mov eax, 3
337748: jmp 0x1403377fb
33774d: mov ecx, 1
337752: cmp word ptr [rdi + 0xf88], cx
337759: jne 0x14033776b
33775b: lea rax, [rdi + 0xce8]
337762: cmp qword ptr [rdi + 0xcd8], rax
337769: je 0x14033776d
33776b: mov ebx, ecx
33776d: lea rax, [rdi + 0xce8]
337774: mov word ptr [rdi + 0xf88], cx
33777b: mov qword ptr [rdi + 0xcd8], rax
337782: lea rax, [rdi + 0xe20]
337789: mov qword ptr [rdi + 0xce0], rax
337790: jmp 0x140337802
337792: mov esi, 7
337797: cmp word ptr [rdi + 0xf88], bx
33779e: jne 0x1403377b0
3377a0: lea rax, [rdi + 0xce8]
3377a7: cmp qword ptr [rdi + 0xcd8], rax
3377ae: je 0x1403377b5
3377b0: mov ebx, 1
3377b5: lea rax, [rdi + 0xce8]
3377bc: mov word ptr [rdi + 0xf88], bp
3377c3: mov qword ptr [rdi + 0xcd8], rax
3377ca: lea rax, [rdi + 0xe20]
3377d1: mov qword ptr [rdi + 0xce0], rax
3377d8: jmp 0x140337802
3377da: lea rax, [rdi + 0xce8]
3377e1: mov qword ptr [rdi + 0xcd8], rax
3377e8: lea rax, [rdi + 0xe20]
3377ef: mov qword ptr [rdi + 0xce0], rax
3377f6: mov eax, 4
3377fb: mov word ptr [rdi + 0xf88], ax
337802: mov rax, qword ptr [rdi]
337805: mov rcx, rdi
337808: movzx edx, word ptr [rdi + 0xf8a]
33780f: call qword ptr [rax + 0x18]
337812: test ebx, ebx
337814: je 0x14033783e
337816: mov rcx, qword ptr [rdi + 0xcd0]
33781d: movzx edx, word ptr [rcx + 0x11a]
337824: call 0x140411cc0
337829: movzx ebx, al
33782c: call 0x14050933c
337831: and eax, 0x7fff
337836: imul eax, ebx
337839: shr eax, 0xf
33783c: jmp 0x140337841
33783e: movzx eax, bp
337841: mov rcx, qword ptr [rdi + 0xcd0]
337848: movzx edx, ax
33784b: call 0x140411610
337850: cmp si, 1
337854: jne 0x140337862
337856: mov rax, qword ptr [rdi]
337859: mov rcx, rdi
33785c: call qword ptr [rax + 0x128]
337862: mov rbx, qword ptr [rsp + 0x30]
337867: movzx eax, si
33786a: mov rsi, qword ptr [rsp + 0x40]
33786f: mov rbp, qword ptr [rsp + 0x38]
337874: add rsp, 0x20
337878: pop rdi
337879: ret 

SLOT 46 RVA 327a30
327a30: mov eax, dword ptr [rcx + 0x1c]
327a33: ret 

SLOT 47 RVA 317df0
317df0: mov dword ptr [r8], 0x100
317df7: xor eax, eax
317df9: mov dword ptr [r8 + 4], 0x100
317e01: mov qword ptr [rdx], rax
317e04: mov dword ptr [rdx + 8], 0x200
317e0b: mov dword ptr [rdx + 0xc], 0x200
317e12: ret 

SLOT 48 RVA 316900
316900: push rbx
316902: sub rsp, 0x40
316906: mov rbx, rcx
316909: movaps xmmword ptr [rsp + 0x30], xmm6
31690e: mov ecx, dword ptr [rcx + 0x14]
316911: movaps xmmword ptr [rsp + 0x20], xmm7
316916: test ecx, ecx
316918: jne 0x140316938
31691a: movzx eax, byte ptr [rbx + 0x5f0]
316921: lea ecx, [rax*8 - 8]
316928: mov dword ptr [rbx + 0x14], ecx
31692b: cmp ecx, 1
31692e: jge 0x140316938
316930: mov ecx, 1
316935: mov dword ptr [rbx + 0x14], ecx
316938: movd xmm0, ecx
31693c: mov eax, ecx
31693e: neg eax
316940: mov dword ptr [rbx + 0xc], eax
316943: cvtdq2pd xmm0, xmm0
316947: mulsd xmm0, qword ptr [rip + 0x296509]
31694f: cvttsd2si eax, xmm0
316953: mov dword ptr [rbx + 0x18], eax
316956: neg eax
316958: mov dword ptr [rbx + 0x10], eax
31695b: mov rcx, qword ptr [rip + 0x350bfe]
316962: call 0x14041a1a0
316967: movd xmm4, dword ptr [rbx + 0xc]
31696c: movd xmm5, dword ptr [rbx + 0x14]
316971: movd xmm6, dword ptr [rbx + 0x10]
316976: movd xmm7, dword ptr [rbx + 0x18]
31697b: cvtdq2ps xmm4, xmm4
31697e: cvtdq2ps xmm5, xmm5
316981: cvtdq2ps xmm6, xmm6
316984: cvtdq2ps xmm7, xmm7
316987: test eax, eax
316989: je 0x140316995
31698b: movss xmm0, dword ptr [rip + 0x28bbad]
316993: jmp 0x14031699d
316995: movss xmm0, dword ptr [rip + 0x2964b7]
31699d: movaps xmm3, xmm0
3169a0: mulss xmm5, xmm0
3169a4: mulss xmm4, xmm3
3169a8: movaps xmm1, xmm0
3169ab: mulss xmm6, xmm1
3169af: movaps xmm2, xmm0
3169b2: cvttss2si eax, xmm4
3169b6: mulss xmm7, xmm2
3169ba: mov dword ptr [rbx + 0xc], eax
3169bd: cvttss2si eax, xmm5
3169c1: mov dword ptr [rbx + 0x14], eax
3169c4: cvttss2si eax, xmm6
3169c8: movaps xmm6, xmmword ptr [rsp + 0x30]
3169cd: mov dword ptr [rbx + 0x10], eax
3169d0: cvttss2si eax, xmm7
3169d4: movaps xmm7, xmmword ptr [rsp + 0x20]
3169d9: mov dword ptr [rbx + 0x18], eax
3169dc: add rsp, 0x40
3169e0: pop rbx
3169e1: ret 

SLOT 49 RVA 3373e0
3373e0: movzx eax, word ptr [rsp + 0x28]
3373e5: mov word ptr [rcx + 0x36], ax
3373e9: movzx eax, word ptr [rsp + 0x30]
3373ee: mov word ptr [rcx + 0x38], ax
3373f2: movzx eax, word ptr [rsp + 0x38]
3373f7: mov word ptr [rcx + 0x3a], ax
3373fb: movzx eax, word ptr [rsp + 0x40]
337400: mov word ptr [rcx + 0x3c], ax
337404: movzx eax, word ptr [rsp + 0x48]
337409: mov word ptr [rcx + 0x3e], ax
33740d: movzx eax, word ptr [rsp + 0x50]
337412: mov word ptr [rcx + 0x40], ax
337416: movzx eax, word ptr [rsp + 0x58]
33741b: mov word ptr [rcx + 0x42], ax
33741f: movzx eax, word ptr [rsp + 0x60]
337424: mov word ptr [rcx + 0x44], ax
337428: movzx eax, word ptr [rsp + 0x68]
33742d: mov word ptr [rcx + 0x46], ax
337431: movzx eax, word ptr [rsp + 0x70]
337436: mov word ptr [rcx + 0x48], ax
33743a: movzx eax, word ptr [rsp + 0x78]
33743f: mov word ptr [rcx + 0x4a], ax
337443: movzx eax, word ptr [rsp + 0x80]
33744b: mov word ptr [rcx + 0x4c], ax
33744f: movzx eax, word ptr [rsp + 0x88]
337457: mov word ptr [rcx + 0x4e], ax
33745b: mov word ptr [rcx + 0x30], dx
33745f: mov word ptr [rcx + 0x32], r8w
337464: mov word ptr [rcx + 0x34], r9w
337469: ret 

SLOT 50 RVA 327120
327120: movzx eax, dl
327123: mov r10, rcx
327126: cmp dl, 5
327129: ja 0x14032715c
32712b: cmp r8b, 0xa
32712f: ja 0x14032715c
327131: cmp r9b, 0x64
327135: jbe 0x14032713a
327137: mov al, 0xf
327139: ret 

SLOT 51 RVA b30c0
b30c0: mov eax, 1
b30c5: ret 

SLOT 52 RVA b30c0
b30c0: mov eax, 1
b30c5: ret 

SLOT 53 RVA 331440
331440: mov byte ptr [rcx + 0x5f4], dl
331446: ret 

SLOT 54 RVA 331450
331450: mov byte ptr [rcx + 0x5f5], dl
331456: ret 

SLOT 55 RVA 327180
327180: mov eax, 0x23
327185: ret 

SLOT 56 RVA 3271c0
3271c0: xor eax, eax
3271c2: mov qword ptr [rdx], rax
3271c5: ret 

SLOT 57 RVA 327940
327940: mov rax, qword ptr [rcx + 0xcd0]
327947: movzx r9d, word ptr [rax + 0x11a]
32794f: mov word ptr [rdx], r9w
327953: mov rax, qword ptr [rcx + 0xcd0]
32795a: movzx ecx, word ptr [rax + 0x118]
327961: mov al, 1
327963: mov word ptr [r8], cx
327967: ret 

SLOT 58 RVA 327330
327330: mov qword ptr [rsp + 0x10], rbx
327335: mov qword ptr [rsp + 0x18], rsi
32733a: push rdi
32733b: sub rsp, 0x20
32733f: mov rcx, qword ptr [rcx + 0xcd0]
327346: mov rbx, rdx
327349: add rcx, 0x110
327350: lea rdx, [rsp + 0x30]
327355: mov rsi, r9
327358: mov rdi, r8
32735b: call 0x1403fff70
327360: mov rdx, rax
327363: mov rcx, rbx
327366: call 0x1403fd770
32736b: lea rcx, [rsp + 0x30]
327370: call 0x1403fd740
327375: lea rdx, [rip + 0x2c4431]
32737c: mov rcx, rdi
32737f: call 0x1403fd810
327384: lea rdx, [rip + 0x2c4422]
32738b: mov rcx, rsi
32738e: call 0x1403fd810
327393: mov rcx, qword ptr [rsp + 0x50]
327398: lea rdx, [rip + 0x2c440e]
32739f: call 0x1403fd810
3273a4: mov rbx, qword ptr [rsp + 0x38]
3273a9: mov al, 1
3273ab: mov rsi, qword ptr [rsp + 0x40]
3273b0: add rsp, 0x20
3273b4: pop rdi
3273b5: ret 

SLOT 59 RVA 1e1e0
1e1e0: ret 0

SLOT 60 RVA 32a7f0
32a7f0: mov qword ptr [rsp + 0x20], rbx
32a7f5: push rsi
32a7f6: push r14
32a7f8: push r15
32a7fa: sub rsp, 0x40
32a7fe: mov rbx, rcx
32a801: mov r14, r8
32a804: mov ecx, 0x800
32a809: mov r15, rdx
32a80c: call 0x140502678
32a811: lea r8, [rsp + 0x60]
32a816: mov rcx, rbx
32a819: lea rdx, [rsp + 0x70]
32a81e: mov rsi, rax
32a821: call 0x14032a5f0
32a826: lea rcx, [rbx + 0xdf8]
32a82d: lea rdx, [rsp + 0x68]
32a832: call 0x1403fff70
32a837: mov r8, qword ptr [rsp + 0x68]
32a83c: lea rdx, [rsp + 0x60]
32a841: lea rcx, [rsp + 0x68]
32a846: mov r9d, dword ptr [r8 - 8]
32a84a: xor r8d, r8d
32a84d: add r9d, -2
32a851: call 0x1403ff050
32a856: mov rdx, rax
32a859: lea rcx, [rsp + 0x68]
32a85e: call 0x1403fd770
32a863: lea rcx, [rsp + 0x60]
32a868: call 0x1403fd740
32a86d: mov rax, qword ptr [rsp + 0x68]
32a872: lea r8, [rip + 0x281fb7]
32a879: mov r9, qword ptr [rsp + 0x70]
32a87e: mov edx, 0x800
32a883: mov qword ptr [rsp + 0x30], rax
32a888: mov rcx, rsi
32a88b: mov eax, dword ptr [rbx + 0xf90]
32a891: mov dword ptr [rsp + 0x28], eax
32a895: mov eax, dword ptr [rbx + 0xf8c]
32a89b: mov dword ptr [rsp + 0x20], eax
32a89f: call 0x14029a8f0
32a8a4: mov rcx, qword ptr [rsp + 0x70]
32a8a9: movsxd rbx, eax
32a8ac: call 0x1404fdab8
32a8b1: mov byte ptr [rbx + rsi], 0
32a8b5: mov rcx, rsi
32a8b8: mov dword ptr [r14], ebx
32a8bb: call 0x14051beb8
32a8c0: mov rcx, rsi
32a8c3: mov qword ptr [r15], rax
32a8c6: call 0x1404fdab8
32a8cb: lea rcx, [rsp + 0x68]
32a8d0: call 0x1403fd740
32a8d5: mov rbx, qword ptr [rsp + 0x78]
32a8da: add rsp, 0x40
32a8de: pop r15
32a8e0: pop r14
32a8e2: pop rsi
32a8e3: ret 

SLOT 61 RVA 33ec40
33ec40: mov qword ptr [rsp + 0x20], rbx
33ec45: mov qword ptr [rsp + 0x10], rdx
33ec4a: push rbp
33ec4b: push rsi
33ec4c: push r14
33ec4e: lea rbp, [rsp - 0x47]
33ec53: sub rsp, 0xb0
33ec5a: mov rax, qword ptr [rip + 0x325d77]
33ec61: xor rax, rsp
33ec64: mov qword ptr [rbp + 0x37], rax
33ec68: mov rsi, rcx
33ec6b: mov edx, 0xa
33ec70: lea rcx, [rbp - 0x29]
33ec74: call 0x1404073a0
33ec79: lea r14, [rip + 0x251cb8]
33ec80: lea rdx, [rip + 0x2acb26]
33ec87: mov qword ptr [rbp - 0x29], r14
33ec8b: lea rcx, [rbp + 0xf]
33ec8f: call 0x1403fd6b0
33ec94: lea rdx, [rbp - 0x49]
33ec98: mov qword ptr [rbp + 0x17], 0
33eca0: lea rcx, [rbp + 0x6f]
33eca4: call 0x1403fff70
33eca9: mov rdx, rax
33ecac: lea rcx, [rbp - 0x29]
33ecb0: call 0x140306fc0
33ecb5: lea rcx, [rbp - 0x49]
33ecb9: call 0x1403fd740
33ecbe: lea rdx, [rip + 0x26d133]
33ecc5: lea rcx, [rbp - 0x49]
33ecc9: call 0x1403fd6b0
33ecce: lea rdx, [rbp - 0x49]
33ecd2: lea rcx, [rbp - 0x29]
33ecd6: call 0x140306f50
33ecdb: lea rcx, [rbp - 0x49]
33ecdf: mov rbx, rax
33ece2: call 0x1403fd740
33ece7: mov rdx, rbx
33ecea: mov rcx, rsi
33eced: call 0x14033e450
33ecf2: test al, al
33ecf4: je 0x14033ee53
33ecfa: lea rdx, [rip + 0x26db1f]
33ed01: lea rcx, [rbp - 0x49]
33ed05: call 0x1403fd6b0
33ed0a: lea rdx, [rbp - 0x49]
33ed0e: lea rcx, [rbp - 0x29]
33ed12: call 0x140306f50
33ed17: lea rcx, [rbp - 0x49]
33ed1b: mov rbx, rax
33ed1e: call 0x1403fd740
33ed23: test rbx, rbx
33ed26: je 0x14033ee53
33ed2c: mov rbx, qword ptr [rbx + 8]
33ed30: test rbx, rbx
33ed33: je 0x14033ee4f
33ed39: mov qword ptr [rsp + 0xe0], rdi
33ed41: mov rdi, qword ptr [rbx + 0x10]
33ed45: lea rcx, [rbp - 0x49]
33ed49: lea rdx, [rdi + 8]
33ed4d: call 0x1403fd640
33ed52: lea rcx, [rbp - 0x49]
33ed56: call 0x1403fe650
33ed5b: mov rcx, qword ptr [rbp - 0x49]
33ed5f: call 0x14043f480
33ed64: cmp eax, 0x52534552
33ed69: je 0x14033eda5
33ed6b: cmp eax, 0x534c4146
33ed70: je 0x14033ed91
33ed72: cmp eax, 0x55564e49
33ed77: jne 0x14033ee32
33ed7d: mov rcx, qword ptr [rdi + 0x10]
33ed81: call 0x140503d20
33ed86: mov dword ptr [rsi + 0xf90], eax
33ed8c: jmp 0x14033ee32
33ed91: mov rcx, qword ptr [rdi + 0x10]
33ed95: call 0x140503d20
33ed9a: mov dword ptr [rsi + 0xf8c], eax
33eda0: jmp 0x14033ee32
33eda5: lea r8, [rip + 0x26c6ec]
33edac: lea rdx, [rdi + 0x10]
33edb0: lea rcx, [rbp - 0x41]
33edb4: call 0x1403fd8e0
33edb9: mov rdx, rax
33edbc: lea rcx, [rbp + 0x27]
33edc0: call 0x1403ff710
33edc5: mov r9d, 1
33edcb: lea rcx, [rsi + 0xdf0]
33edd2: mov r8d, r9d
33edd5: lea rdx, [rbp + 0x27]
33edd9: call 0x14014d080
33edde: lea rcx, [rbp - 0x41]
33ede2: call 0x1403fd740
33ede7: cmp dword ptr [rip + 0x3d0f2a], 0
33edee: jne 0x14033ee32
33edf0: lea r8, [rip + 0x26c7b1]
33edf7: lea rdx, [rdi + 0x10]
33edfb: lea rcx, [rbp - 0x39]
33edff: call 0x1403fd8e0
33ee04: mov rdx, rax
33ee07: lea rcx, [rbp + 0x2f]
33ee0b: call 0x1403ff710
33ee10: mov r9d, 1
33ee16: lea rcx, [rsi + 0xf28]
33ee1d: mov r8d, r9d
33ee20: lea rdx, [rbp + 0x2f]
33ee24: call 0x14014d080
33ee29: lea rcx, [rbp - 0x39]
33ee2d: call 0x1403fd740
33ee32: lea rcx, [rbp - 0x49]
33ee36: call 0x1403fd740
33ee3b: mov rbx, qword ptr [rbx]
33ee3e: test rbx, rbx
33ee41: jne 0x14033ed41
33ee47: mov rdi, qword ptr [rsp + 0xe0]
33ee4f: mov bl, 1
33ee51: jmp 0x14033ee55
33ee53: xor bl, bl
33ee55: lea rcx, [rbp - 0x29]
33ee59: mov qword ptr [rbp - 0x29], r14
33ee5d: call 0x140306e80
33ee62: lea rcx, [rbp + 0xf]
33ee66: call 0x1403fd740
33ee6b: lea rcx, [rbp - 0x29]
33ee6f: call 0x1404073d0
33ee74: movzx eax, bl
33ee77: mov rcx, qword ptr [rbp + 0x37]
33ee7b: xor rcx, rsp
33ee7e: call 0x1404f77a0
33ee83: mov rbx, qword ptr [rsp + 0xe8]
33ee8b: add rsp, 0xb0
33ee92: pop r14
33ee94: pop rsi
33ee95: pop rbp
33ee96: ret 