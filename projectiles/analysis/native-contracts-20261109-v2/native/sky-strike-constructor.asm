227cd0: push rbx
227cd2: push rbp
227cd3: push rsi
227cd4: push rdi
227cd5: push r14
227cd7: push r15
227cd9: sub rsp, 0x38
227cdd: mov rax, qword ptr [rip + 0x43ccf4] ; b'2\xa2\xdf-\x99+'
227ce4: xor rax, rsp
227ce7: mov qword ptr [rsp + 0x28], rax
227cec: movzx r14d, r9b
227cf0: mov r15, r8
227cf3: mov rbx, rdx
227cf6: mov rdi, rcx
227cf9: call 0x226910
227cfe: lea rax, [rip + 0x37454b] ; b''
227d05: lea rcx, [rdi + 0x1b8]
227d0c: mov qword ptr [rdi], rax
227d0f: call 0x410f70
227d14: movzx edx, word ptr [rip + 0x398961] ; b'\x01'
227d1b: lea rcx, [rdi + 0x2f0]
227d22: call 0x421010
227d27: mov rdx, rbx
227d2a: lea rcx, [rsp + 0x20]
227d2f: call 0x3ff710
227d34: mov r9d, 1
227d3a: lea rcx, [rdi + 0x2c0]
227d41: mov r8d, r9d
227d44: lea rdx, [rsp + 0x20]
227d49: call 0x14d080
227d4e: cmp r14b, 0xff
227d52: je 0x227d8e
227d54: mov rax, qword ptr [rip + 0x43f7ed] ; b''
227d5b: lea rcx, [rdi + 0x2f0]
227d62: movzx r8d, r14b
227d66: xor edx, edx
227d68: mov r9, qword ptr [rax + 0x1090]
227d6f: add r9, 0x63d8
227d76: call 0x4221c0
227d7b: lea rdx, [rdi + 0x2f0]
227d82: lea rcx, [rdi + 0x1b8]
227d89: call 0x412390
227d8e: xor edx, edx
227d90: lea rcx, [rdi + 0x1b8]
227d97: call 0x411610
227d9c: lea rcx, [rdi + 0x140]
227da3: mov r8, r15
227da6: lea rdx, [rsp + 0x20]
227dab: call 0x3ff890
227db0: mov ecx, dword ptr [rsp + 0x90]
227db7: mov rax, rdi
227dba: mov dword ptr [rdi + 0x320], ecx
227dc0: movzx ecx, word ptr [rsp + 0x98]
227dc8: mov word ptr [rdi + 0x324], cx
227dcf: mov rcx, qword ptr [rsp + 0x28]
227dd4: xor rcx, rsp
227dd7: call 0x4f77a0
227ddc: add rsp, 0x38
227de0: pop r15
227de2: pop r14
227de4: pop rdi
227de5: pop rsi
227de6: pop rbp
227de7: pop rbx
227de8: ret 
227de9: int3 
227dea: int3 
227deb: int3 
227dec: int3 
227ded: int3 
227dee: int3 
227def: int3 
