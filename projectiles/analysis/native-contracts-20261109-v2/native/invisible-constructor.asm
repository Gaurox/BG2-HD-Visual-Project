227a40: mov qword ptr [rsp + 0x10], rbx
227a45: push rdi
227a46: sub rsp, 0x20
227a4a: mov rdi, rcx
227a4d: lea rdx, [rip + 0x374ff4] ; b'SPFIREBL'
227a54: lea rcx, [rsp + 0x30]
227a59: call 0x3ff800
227a5e: mov rcx, rdi
227a61: mov rdx, qword ptr [rax]
227a64: call 0x227600
227a69: mov rcx, qword ptr [rdi + 0x1b8]
227a70: lea rax, [rip + 0x3737f1] ; b'\xd0\x81"@\x01'
227a77: xor edx, edx
227a79: mov qword ptr [rdi], rax
227a7c: call 0x412380
227a81: mov rax, qword ptr [rip + 0x43fac0] ; b''
227a88: lea rcx, [rdi + 0x1c8]
227a8f: xor edx, edx
227a91: mov r9, qword ptr [rax + 0x1090]
227a98: add r9, 0x63d8
227a9f: lea r8d, [rdx + 0x43]
227aa3: call 0x4221c0
227aa8: mov rcx, qword ptr [rdi + 0x1b8]
227aaf: lea rdx, [rdi + 0x1c8]
227ab6: call 0x412390
227abb: mov eax, 5
227ac0: mov dword ptr [rdi + 0x21c], 0
227aca: lea rcx, [rdi + 0x178]
227ad1: mov word ptr [rdi + 0x214], ax
227ad8: lea rdx, [rip + 0x3c3cce] ; b''
227adf: mov dword ptr [rdi + 0x70], 0xffffffff
227ae6: call 0x3fd810
227aeb: mov rbx, qword ptr [rsp + 0x38]
227af0: mov rax, rdi
227af3: mov dword ptr [rdi + 0x180], 0xffffffff
227afd: mov byte ptr [rdi + 0x341], 1
227b04: add rsp, 0x20
227b08: pop rdi
227b09: ret 
