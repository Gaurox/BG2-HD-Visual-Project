233f20: mov r11, rsp
233f23: push rbp
233f24: push r12
233f26: push r14
233f28: lea rbp, [r11 - 0x5f]
233f2c: sub rsp, 0xc0
233f33: mov rax, qword ptr [rip + 0x430a9e] ; b'2\xa2\xdf-\x99+'
233f3a: xor rax, rsp
233f3d: mov qword ptr [rbp + 0x17], rax
233f41: cmp qword ptr [rcx + 0x18], 0
233f46: mov r12, r8
233f49: mov r14, rcx
233f4c: je 0x234505
233f52: movzx edx, byte ptr [rip + 0x38c726] ; b'\xff\x0c'
233f59: mov qword ptr [r11 + 0x10], rbx
233f5d: mov eax, edx
233f5f: shl eax, 0x10
233f62: mov ebx, edx
233f64: shl ebx, 8
233f67: or ebx, eax
233f69: mov qword ptr [r11 - 0x28], rdi
233f6d: mov rax, qword ptr [rcx]
233f70: or ebx, edx
233f72: mov qword ptr [r11 - 0x30], r13
233f76: xor r13d, r13d
233f79: mov qword ptr [rbp + 7], r13
233f7d: call qword ptr [rax + 0xf8]
233f83: mov edi, eax
233f85: cmp dword ptr [r14 + 0x21c], r13d
233f8c: je 0x2344ed
