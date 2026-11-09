227b10: mov qword ptr [rsp + 0x10], rbx
227b15: push rdi
227b16: sub rsp, 0x30
227b1a: mov rax, qword ptr [rip + 0x43ceb7] ; b'2\xa2\xdf-\x99+'
227b21: xor rax, rsp
227b24: mov qword ptr [rsp + 0x28], rax
227b29: mov rdi, rcx
227b2c: lea rdx, [rip + 0x371a81] ; b'SPBOOM'
227b33: lea rcx, [rsp + 0x20]
227b38: call 0x3ff800
227b3d: mov rcx, rdi
227b40: mov rdx, qword ptr [rax]
227b43: call 0x227600
227b48: mov rcx, qword ptr [rdi + 0x1b8]
227b4f: lea rax, [rip + 0x373aca] ; b'\xd0\x81"@\x01'
227b56: xor edx, edx
227b58: mov qword ptr [rdi], rax
227b5b: call 0x412380
227b60: mov rax, qword ptr [rip + 0x43f9e1] ; b''
227b67: lea rcx, [rdi + 0x1c8]
227b6e: xor edx, edx
227b70: mov r9, qword ptr [rax + 0x1090]
227b77: add r9, 0x63d8
227b7e: lea r8d, [rdx + 0x43]
227b82: call 0x4221c0
227b87: mov rcx, qword ptr [rdi + 0x1b8]
227b8e: lea rdx, [rdi + 0x1c8]
227b95: call 0x412390
227b9a: xor eax, eax
227b9c: lea rcx, [rdi + 0x140]
227ba3: lea r8, [rip + 0x3c3c03] ; b''
227baa: mov qword ptr [rdi + 0x1f8], rax
227bb1: lea rdx, [rsp + 0x20]
227bb6: mov dword ptr [rdi + 0x200], eax
227bbc: mov dword ptr [rdi + 0x210], eax
227bc2: call 0x3ff960
227bc7: mov eax, 1
227bcc: mov word ptr [rdi + 0x214], ax
227bd3: mov rax, rdi
227bd6: mov rcx, qword ptr [rsp + 0x28]
227bdb: xor rcx, rsp
227bde: call 0x4f77a0
227be3: mov rbx, qword ptr [rsp + 0x48]
227be8: add rsp, 0x30
227bec: pop rdi
227bed: ret 
