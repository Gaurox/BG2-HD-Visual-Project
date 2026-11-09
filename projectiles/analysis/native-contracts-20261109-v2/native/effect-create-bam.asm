2590ff: lea rcx, [rbx + 0x60]
259103: call 0x3ff890
259108: mov ecx, 0x138
25910d: call 0x4f7a88
259112: test rax, rax
259115: je 0x259125
259117: mov rdx, qword ptr [rbx + 0x60]
25911b: mov rcx, rax
25911e: call 0x410e10
259123: jmp 0x259128
259125: mov rax, rsi
259128: mov r9d, dword ptr [rbx + 0xa4]
25912f: lea r8, [rbp - 0x48]
259133: mov qword ptr [rbx + 0x248], rax
25913a: mov rdx, r12
25913d: movzx eax, byte ptr [rip + 0x3405e3] ; b''
259144: mov rcx, rbx
259147: mov dword ptr [rsp + 0x28], esi
25914b: mov byte ptr [rsp + 0x20], al
25914f: call 0x253bb0
