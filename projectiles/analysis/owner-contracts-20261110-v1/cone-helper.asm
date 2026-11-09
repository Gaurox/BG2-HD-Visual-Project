227800: mov qword ptr [rsp + 0x10], rbx
227805: push rdi
227806: sub rsp, 0x30
22780a: mov rax, qword ptr [rip + 0x43d1c7] ; b'2\xa2\xdf-\x99+'
227811: xor rax, rsp
227814: mov qword ptr [rsp + 0x28], rax
227819: mov rdi, rcx
22781c: lea rdx, [rip + 0x375245] ; b'SPBRNHND'
227823: lea rcx, [rsp + 0x20]
227828: call 0x3ff800
22782d: mov rcx, rdi
227830: mov rdx, qword ptr [rax]
227833: call 0x227600
227838: mov rcx, qword ptr [rdi + 0x1b8]
22783f: lea rax, [rip + 0x37418a] ; b'\xa0\x82"@\x01'
227846: xor edx, edx
227848: mov qword ptr [rdi], rax
22784b: call 0x412380
227850: mov rax, qword ptr [rip + 0x43fcf1] ; b''
227857: lea rcx, [rdi + 0x1c8]
22785e: xor edx, edx
227860: mov r9, qword ptr [rax + 0x1090]
227867: add r9, 0x63d8
22786e: lea r8d, [rdx + 0x47]
227872: call 0x4221c0
227877: mov rcx, qword ptr [rdi + 0x1b8]
22787e: lea rdx, [rdi + 0x1c8]
227885: call 0x412390
22788a: xor eax, eax
22788c: lea rcx, [rdi + 0x140]
227893: mov qword ptr [rdi + 0x1f8], rax
22789a: lea r8, [rip + 0x3c3f0c] ; b''
2278a1: mov dword ptr [rdi + 0x200], eax
2278a7: lea rdx, [rsp + 0x20]
2278ac: mov dword ptr [rdi + 0x210], eax
2278b2: mov eax, 5
2278b7: mov word ptr [rdi + 0x214], ax
2278be: call 0x3ff960
2278c3: mov eax, 0x37
2278c8: mov dword ptr [rdi + 0x70], 0xffffffff
2278cf: lea rcx, [rdi + 0x178]
2278d6: mov word ptr [rdi + 0x3b8], ax
2278dd: lea rdx, [rip + 0x3c3ec9] ; b''
2278e4: call 0x3fd810
2278e9: mov dword ptr [rsp + 0x20], 0x17
2278f1: mov rax, rdi
2278f4: mov dword ptr [rsp + 0x24], 0x32
2278fc: mov rcx, qword ptr [rsp + 0x20]
227901: mov qword ptr [rdi + 0x164], rcx
227908: mov dword ptr [rdi + 0x180], 0xffffffff
227912: mov rcx, qword ptr [rsp + 0x28]
227917: xor rcx, rsp
22791a: call 0x4f77a0
22791f: mov rbx, qword ptr [rsp + 0x48]
227924: add rsp, 0x30
227928: pop rdi
227929: ret 
