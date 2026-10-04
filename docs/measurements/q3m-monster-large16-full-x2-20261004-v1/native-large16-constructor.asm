00310850 b7e8 mov bh, 0xe8
00310852 7a6b jp 0x3108bf
00310854 0f00488b str word ptr [rax - 0x75]
00310858 05eb6c3500 add eax, 0x356ceb
0031085d 440fb6430a movzx r8d, byte ptr [rbx + 0xa]
00310862 0fb75599 movzx edx, word ptr [rbp - 0x67]
00310866 488b8890100000 mov rcx, qword ptr [rax + 0x1090]
0031086d e8bea5f2ff call 0x23ae30
00310872 488d1534af2d00 lea rdx, [rip + 0x2daf34]
00310879 88430b mov byte ptr [rbx + 0xb], al
0031087c 488d8bf7050000 lea rcx, [rbx + 0x5f7]
00310883 88430a mov byte ptr [rbx + 0xa], al
00310886 e8f5f10e00 call 0x3ffa80
0031088b 85c0 test eax, eax
0031088d 7413 je 0x3108a2
0031088f 4d8bc5 mov r8, r13
00310892 488d5517 lea rdx, [rbp + 0x17]
00310896 488d8bf7050000 lea rcx, [rbx + 0x5f7]
0031089d e8eeef0e00 call 0x3ff890
003108a2 488bcb mov rcx, rbx
003108a5 e856600000 call 0x316900
003108aa 4c8d05e7ab2900 lea r8, [rip + 0x29abe7] ; G1
003108b1 498bd5 mov rdx, r13
003108b4 488d4d07 lea rcx, [rbp + 7]
003108b8 e823d00e00 call 0x3fd8e0
003108bd 488bd0 mov rdx, rax
003108c0 488d4d0f lea rcx, [rbp + 0xf]
003108c4 e847ee0e00 call 0x3ff710
003108c9 bf01000000 mov edi, 1
003108ce 488d8bf80d0000 lea rcx, [rbx + 0xdf8]
003108d5 448bcf mov r9d, edi
003108d8 488d550f lea rdx, [rbp + 0xf]
003108dc 448bc7 mov r8d, edi
003108df e89cc7e3ff call 0x14d080
003108e4 488d4d07 lea rcx, [rbp + 7]
003108e8 e853ce0e00 call 0x3fd740
003108ed 4c8d058cb12900 lea r8, [rip + 0x29b18c] ; G2
003108f4 498bd5 mov rdx, r13
003108f7 488d4d07 lea rcx, [rbp + 7]
003108fb e8e0cf0e00 call 0x3fd8e0
00310900 488bd0 mov rdx, rax
00310903 488d4d0f lea rcx, [rbp + 0xf]
00310907 e804ee0e00 call 0x3ff710
0031090c 488d8b68100000 lea rcx, [rbx + 0x1068]
00310913 448bcf mov r9d, edi
00310916 448bc7 mov r8d, edi
00310919 488d550f lea rdx, [rbp + 0xf]
0031091d e85ec7e3ff call 0x14d080
00310922 488d4d07 lea rcx, [rbp + 7]
00310926 e815ce0e00 call 0x3fd740
0031092b 4c8d058eb42900 lea r8, [rip + 0x29b48e] ; G3
00310932 498bd5 mov rdx, r13
00310935 488d4d07 lea rcx, [rbp + 7]
00310939 e8a2cf0e00 call 0x3fd8e0
0031093e 488bd0 mov rdx, rax
00310941 488d4d0f lea rcx, [rbp + 0xf]
00310945 e8c6ed0e00 call 0x3ff710
0031094a 488d8bd8120000 lea rcx, [rbx + 0x12d8]
00310951 448bcf mov r9d, edi
00310954 448bc7 mov r8d, edi
00310957 488d550f lea rdx, [rbp + 0xf]
0031095b e820c7e3ff call 0x14d080
00310960 488d4d07 lea rcx, [rbp + 7]
00310964 e8d7cd0e00 call 0x3fd740
00310969 4c8db3f00c0000 lea r14, [rbx + 0xcf0]
00310970 4c89b3e00c0000 mov qword ptr [rbx + 0xce0], r14
00310977 498bc6 mov rax, r14
0031097a 833d97f33f0000 cmp dword ptr [rip + 0x3ff397], 0
00310981 0f85c1000000 jne 0x310a48
00310987 4c8d051aac2900 lea r8, [rip + 0x29ac1a] ; G1E
0031098e 498bd5 mov rdx, r13
00310991 488d4d07 lea rcx, [rbp + 7]
00310995 e846cf0e00 call 0x3fd8e0
0031099a 488bd0 mov rdx, rax
0031099d 488d4d0f lea rcx, [rbp + 0xf]
003109a1 e86aed0e00 call 0x3ff710
003109a6 488d8b300f0000 lea rcx, [rbx + 0xf30]
003109ad 448bcf mov r9d, edi
003109b0 448bc7 mov r8d, edi
003109b3 488d550f lea rdx, [rbp + 0xf]
003109b7 e8c4c6e3ff call 0x14d080
003109bc 488d4d07 lea rcx, [rbp + 7]
003109c0 e87bcd0e00 call 0x3fd740
003109c5 4c8d0520b12900 lea r8, [rip + 0x29b120] ; G2E
003109cc 498bd5 mov rdx, r13
003109cf 488d4d07 lea rcx, [rbp + 7]
003109d3 e808cf0e00 call 0x3fd8e0
003109d8 488bd0 mov rdx, rax
003109db 488d4d0f lea rcx, [rbp + 0xf]
003109df e82ced0e00 call 0x3ff710
003109e4 488d8ba0110000 lea rcx, [rbx + 0x11a0]
003109eb 448bcf mov r9d, edi
003109ee 448bc7 mov r8d, edi
003109f1 488d550f lea rdx, [rbp + 0xf]
003109f5 e886c6e3ff call 0x14d080
003109fa 488d4d07 lea rcx, [rbp + 7]
003109fe e83dcd0e00 call 0x3fd740
00310a03 4c8d05bab32900 lea r8, [rip + 0x29b3ba] ; G3E
00310a0a 498bd5 mov rdx, r13
00310a0d 488d4d07 lea rcx, [rbp + 7]
00310a11 e8cace0e00 call 0x3fd8e0
00310a16 488bd0 mov rdx, rax
00310a19 488d4d0f lea rcx, [rbp + 0xf]
00310a1d e8eeec0e00 call 0x3ff710
00310a22 488d8b10140000 lea rcx, [rbx + 0x1410]
00310a29 448bcf mov r9d, edi
00310a2c 448bc7 mov r8d, edi
00310a2f 488d550f lea rdx, [rbp + 0xf]
00310a33 e848c6e3ff call 0x14d080
00310a38 488d4d07 lea rcx, [rbp + 7]
00310a3c e8ffcc0e00 call 0x3fd740
00310a41 488b83e00c0000 mov rax, qword ptr [rbx + 0xce0]
00310a48 83bb7414000000 cmp dword ptr [rbx + 0x1474], 0
00310a4f 4c8dab280e0000 lea r13, [rbx + 0xe28]
00310a56 4c89abe80c0000 mov qword ptr [rbx + 0xce8], r13
00310a5d 488983d80c0000 mov qword ptr [rbx + 0xcd8], rax
00310a64 0f8498000000 je 0x310b02
00310a6a 4032ff xor dil, dil
00310a6d 0f1f00 nop dword ptr [rax]
00310a70 488b05d16a3500 mov rax, qword ptr [rip + 0x356ad1]
00310a77 498bcc mov rcx, r12
00310a7a 450fb607 movzx r8d, byte ptr [r15]
00310a7e 400fb6d7 movzx edx, dil
00310a82 4c8b8890100000 mov r9, qword ptr [rax + 0x1090]
00310a89 4981c1d8630000 add r9, 0x63d8
00310a90 e82b171100 call 0x4221c0
00310a95 40fec7 inc dil
00310a98 4d8d7f01 lea r15, [r15 + 1]
00310a9c 4080ff07 cmp dil, 7
00310aa0 72ce jb 0x310a70
00310aa2 498bd4 mov rdx, r12
00310aa5 498bce mov rcx, r14
00310aa8 e8e3181000 call 0x412390
00310aad 498bd4 mov rdx, r12
00310ab0 488d8b600f0000 lea rcx, [rbx + 0xf60]
00310ab7 e8d4181000 call 0x412390
00310abc 498bd4 mov rdx, r12
00310abf 488d8bd0110000 lea rcx, [rbx + 0x11d0]
00310ac6 e8c5181000 call 0x412390
00310acb 833d46f23f0000 cmp dword ptr [rip + 0x3ff246], 0
00310ad2 7529 jne 0x310afd
00310ad4 498bd4 mov rdx, r12
00310ad7 498bcd mov rcx, r13
00310ada e8b1181000 call 0x412390
00310adf 498bd4 mov rdx, r12
00310ae2 488d8b98100000 lea rcx, [rbx + 0x1098]
00310ae9 e8a2181000 call 0x412390
00310aee 498bd4 mov rdx, r12
00310af1 488d8b08130000 lea rcx, [rbx + 0x1308]
00310af8 e893181000 call 0x412390
00310afd bf01000000 mov edi, 1
00310b02 6689bb70140000 mov word ptr [rbx + 0x1470], di
00310b09 833d08f23f0000 cmp dword ptr [rip + 0x3ff208], 0
00310b10 743a je 0x310b4c
00310b12 83bb7414000000 cmp dword ptr [rbx + 0x1474], 0
00310b19 741c je 0x310b37
00310b1b 440fb60557fb2a00 movzx r8d, byte ptr [rip + 0x2afb57]
00310b23 488d5599 lea rdx, [rbp - 0x67]
00310b27 41b900ff0000 mov r9d, 0xff00
00310b2d 498bcc mov rcx, r12
00310b30 e84b161100 call 0x422180
00310b35 eb15 jmp 0x310b4c
00310b37 c683200e000000 mov byte ptr [rbx + 0xe20], 0
00310b3e c6839010000000 mov byte ptr [rbx + 0x1090], 0
00310b45 c6830013000000 mov byte ptr [rbx + 0x1300], 0
