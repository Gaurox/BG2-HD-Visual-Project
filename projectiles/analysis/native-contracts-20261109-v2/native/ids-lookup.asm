11b480: cmp dword ptr [rcx + 0x58], 0
11b484: je 0x11b49b
11b486: cmp edx, dword ptr [rcx + 0x68]
11b489: jge 0x11b4b4
11b48b: test edx, edx
11b48d: jle 0x11b4b4
11b48f: mov rax, qword ptr [rcx + 0x60]
11b493: movsxd rdx, edx
11b496: mov rax, qword ptr [rax + rdx*8]
11b49a: ret 
11b49b: mov rcx, qword ptr [rcx + 0x28]
11b49f: test rcx, rcx
11b4a2: je 0x11b4b4
11b4a4: mov rax, qword ptr [rcx + 0x10]
11b4a8: mov rcx, qword ptr [rcx]
11b4ab: cmp edx, dword ptr [rax]
11b4ad: je 0x11b4b6
11b4af: test rcx, rcx
11b4b2: jne 0x11b4a4
11b4b4: xor eax, eax
11b4b6: ret 
