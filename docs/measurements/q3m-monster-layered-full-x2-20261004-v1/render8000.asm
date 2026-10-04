Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  000000014032F3B0: push        rbp
  000000014032F3B2: push        rsi
  000000014032F3B3: push        rdi
  000000014032F3B4: push        r12
  000000014032F3B6: push        r13
  000000014032F3B8: push        r14
  000000014032F3BA: push        r15
  000000014032F3BC: lea         rbp,[rsp-7]
  000000014032F3C1: sub         rsp,0A0h
  000000014032F3C8: mov         rax,qword ptr [00000001406649D8h]
  000000014032F3CF: xor         rax,rsp
  000000014032F3D2: mov         qword ptr [rbp-9],rax
  000000014032F3D6: mov         rax,qword ptr [rbp+67h]
  000000014032F3DA: mov         rsi,rcx
  000000014032F3DD: mov         rcx,qword ptr [rbp+0000000000000087h]
  000000014032F3E4: mov         r12,rdx
  000000014032F3E7: movups      xmm0,xmmword ptr [r9]
  000000014032F3EB: mov         edi,dword ptr [rbp+000000000000009Fh]
  000000014032F3F1: mov         r14,qword ptr [rbp+6Fh]
  000000014032F3F5: movzx       r13d,byte ptr [rbp+00000000000000A7h]
  000000014032F3FD: mov         qword ptr [rbp-51h],rcx
  000000014032F401: mov         rcx,qword ptr [rbp+00000000000000AFh]
  000000014032F408: mov         qword ptr [rbp-49h],rcx
  000000014032F40C: mov         rcx,qword ptr [rax]
  000000014032F40F: mov         qword ptr [rbp-59h],rcx
  000000014032F413: shr         rcx,20h
  000000014032F417: add         ecx,edi
  000000014032F419: movaps      xmmword ptr [rbp-29h],xmm0
  000000014032F41D: cmp         dword ptr [000000014070FD18h],0
  000000014032F424: mov         dword ptr [rbp-55h],ecx
  000000014032F427: mov         ecx,dword ptr [rbp+77h]
  000000014032F42A: je          000000014032F454
  000000014032F42C: movzx       eax,byte ptr [rsi+0000000000001758h]
  000000014032F433: cmp         word ptr [rsi+000000000000172Ah],ax
  000000014032F43A: jle         000000014032F442
  000000014032F43C: or          ecx,dword ptr [00000001405A234Ch]
  000000014032F442: test        r13b,r13b
  000000014032F445: jne         000000014032F457
  000000014032F447: mov         eax,dword ptr [00000001405A2348h]
  000000014032F44D: or          eax,1
  000000014032F450: or          ecx,eax
  000000014032F452: jmp         000000014032F45D
  000000014032F454: or          ecx,4
  000000014032F457: or          ecx,dword ptr [00000001405A2344h]
  000000014032F45D: mov         r15d,ecx
  000000014032F460: mov         qword ptr [rsp+20h],r14
  000000014032F465: or          r15d,2
  000000014032F469: lea         r9,[rbp-59h]
  000000014032F46D: test        r13b,r13b
  000000014032F470: lea         rdx,[rbp-29h]
  000000014032F474: cmove       r15d,ecx
  000000014032F478: mov         rcx,r12
  000000014032F47B: mov         r8d,r15d
  000000014032F47E: call        000000014029E1B0
  000000014032F483: mov         r8d,r15d
  000000014032F486: lea         rdx,[rbp-29h]
  000000014032F48A: mov         rcx,r12
  000000014032F48D: call        000000014029E190
  000000014032F492: test        eax,eax
  000000014032F494: je          000000014032F870
  000000014032F49A: cmp         dword ptr [rsi+0000000000000BA8h],0
  000000014032F4A1: mov         qword ptr [rsp+00000000000000F0h],rbx
  000000014032F4A9: je          000000014032F4F0
  000000014032F4AB: mov         rcx,qword ptr [rsi+0000000000000CB0h]
  000000014032F4B2: call        00000001403F6D50
  000000014032F4B7: mov         rbx,qword ptr [rsi+0000000000000CB0h]
  000000014032F4BE: mov         rcx,rbx
  000000014032F4C1: call        00000001403F7890
  000000014032F4C6: mov         rcx,rbx
  000000014032F4C9: mov         edi,eax
  000000014032F4CB: call        00000001403F78B0
  000000014032F4D0: movzx       r9d,word ptr [00000001405C0678h]
  000000014032F4D8: mov         rdx,rax
  000000014032F4DB: mov         rcx,qword ptr [rsi+0000000000000CD8h]
  000000014032F4E2: mov         r8d,edi
  000000014032F4E5: call        00000001404123C0
  000000014032F4EA: mov         edi,dword ptr [rbp+000000000000009Fh]
  000000014032F4F0: mov         rcx,qword ptr [rsi+0000000000000CD8h]
  000000014032F4F7: mov         ebx,dword ptr [rbp+7Fh]
  000000014032F4FA: add         rcx,8
  000000014032F4FE: mov         edx,ebx
  000000014032F500: call        0000000140412690
  000000014032F505: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F50C: je          000000014032F525
  000000014032F50E: mov         rcx,qword ptr [rsi+0000000000001200h]
  000000014032F515: test        rcx,rcx
  000000014032F518: je          000000014032F525
  000000014032F51A: add         rcx,8
  000000014032F51E: mov         edx,ebx
  000000014032F520: call        0000000140412690
  000000014032F525: cmp         dword ptr [000000014070FD18h],0
  000000014032F52C: je          000000014032F557
  000000014032F52E: movsx       ecx,word ptr [rsi+000000000000172Ah]
  000000014032F535: movzx       eax,byte ptr [rsi+0000000000001758h]
  000000014032F53C: cmp         ecx,eax
  000000014032F53E: jle         000000014032F557
  000000014032F540: mov         eax,10h
  000000014032F545: sub         eax,ecx
  000000014032F547: and         eax,8000000Fh
  000000014032F54C: jge         000000014032F55E
  000000014032F54E: dec         eax
  000000014032F550: or          eax,0FFFFFFF0h
  000000014032F553: inc         eax
  000000014032F555: jmp         000000014032F55E
  000000014032F557: movzx       eax,word ptr [rsi+000000000000172Ah]
  000000014032F55E: movsx       rcx,ax
  000000014032F562: cmp         ecx,0Fh
  000000014032F565: ja          000000014032F704
  000000014032F56B: lea         rdx,[0000000140000000h]
  000000014032F572: mov         ecx,dword ptr [rdx+rcx*4+000000000032F890h]
  000000014032F579: add         rcx,rdx
  000000014032F57C: jmp         rcx
  000000014032F57E: mov         r9d,dword ptr [r14+4]
  000000014032F582: mov         rcx,r12
  000000014032F585: mov         r8d,dword ptr [r14]
  000000014032F588: mov         rdx,qword ptr [rsi+0000000000000CD8h]
  000000014032F58F: movzx       ebx,r13b
  000000014032F593: mov         dword ptr [rsp+28h],ebx
  000000014032F597: mov         dword ptr [rsp+20h],r15d
  000000014032F59C: call        000000014029E260
  000000014032F5A1: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F5A8: je          000000014032F704
  000000014032F5AE: jmp         000000014032F6E0
  000000014032F5B3: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F5BA: je          000000014032F5ED
  000000014032F5BC: cmp         dword ptr [rsi+0000000000001734h],0
  000000014032F5C3: jne         000000014032F5ED
  000000014032F5C5: mov         rdx,qword ptr [rsi+0000000000001200h]
  000000014032F5CC: test        rdx,rdx
  000000014032F5CF: je          000000014032F5ED
  000000014032F5D1: mov         r9d,dword ptr [r14+4]
  000000014032F5D5: mov         rcx,r12
  000000014032F5D8: mov         r8d,dword ptr [r14]
  000000014032F5DB: movzx       eax,r13b
  000000014032F5DF: mov         dword ptr [rsp+28h],eax
  000000014032F5E3: mov         dword ptr [rsp+20h],r15d
  000000014032F5E8: call        000000014029E260
  000000014032F5ED: mov         r9d,dword ptr [r14+4]
  000000014032F5F1: mov         rcx,r12
  000000014032F5F4: mov         r8d,dword ptr [r14]
  000000014032F5F7: mov         rdx,qword ptr [rsi+0000000000000CD8h]
  000000014032F5FE: movzx       ebx,r13b
  000000014032F602: mov         dword ptr [rsp+28h],ebx
  000000014032F606: mov         dword ptr [rsp+20h],r15d
  000000014032F60B: call        000000014029E260
  000000014032F610: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F617: je          000000014032F704
  000000014032F61D: cmp         dword ptr [rsi+0000000000001734h],0
  000000014032F624: je          000000014032F704
  000000014032F62A: jmp         000000014032F6E0
  000000014032F62F: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F636: je          000000014032F660
  000000014032F638: mov         rdx,qword ptr [rsi+0000000000001200h]
  000000014032F63F: test        rdx,rdx
  000000014032F642: je          000000014032F660
  000000014032F644: mov         r9d,dword ptr [r14+4]
  000000014032F648: mov         rcx,r12
  000000014032F64B: mov         r8d,dword ptr [r14]
  000000014032F64E: movzx       eax,r13b
  000000014032F652: mov         dword ptr [rsp+28h],eax
  000000014032F656: mov         dword ptr [rsp+20h],r15d
  000000014032F65B: call        000000014029E260
  000000014032F660: mov         rdx,qword ptr [rsi+0000000000000CD8h]
  000000014032F667: movzx       eax,r13b
  000000014032F66B: mov         dword ptr [rsp+28h],eax
  000000014032F66F: jmp         000000014032F6F0
  000000014032F671: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F678: je          000000014032F6AB
  000000014032F67A: cmp         dword ptr [rsi+0000000000001734h],0
  000000014032F681: je          000000014032F6AB
  000000014032F683: mov         rdx,qword ptr [rsi+0000000000001200h]
  000000014032F68A: test        rdx,rdx
  000000014032F68D: je          000000014032F6AB
  000000014032F68F: mov         r9d,dword ptr [r14+4]
  000000014032F693: mov         rcx,r12
  000000014032F696: mov         r8d,dword ptr [r14]
  000000014032F699: movzx       eax,r13b
  000000014032F69D: mov         dword ptr [rsp+28h],eax
  000000014032F6A1: mov         dword ptr [rsp+20h],r15d
  000000014032F6A6: call        000000014029E260
  000000014032F6AB: mov         r9d,dword ptr [r14+4]
  000000014032F6AF: mov         rcx,r12
  000000014032F6B2: mov         r8d,dword ptr [r14]
  000000014032F6B5: mov         rdx,qword ptr [rsi+0000000000000CD8h]
  000000014032F6BC: movzx       ebx,r13b
  000000014032F6C0: mov         dword ptr [rsp+28h],ebx
  000000014032F6C4: mov         dword ptr [rsp+20h],r15d
  000000014032F6C9: call        000000014029E260
  000000014032F6CE: cmp         dword ptr [rsi+000000000000172Ch],0
  000000014032F6D5: je          000000014032F704
  000000014032F6D7: cmp         dword ptr [rsi+0000000000001734h],0
  000000014032F6DE: jne         000000014032F704
  000000014032F6E0: mov         rdx,qword ptr [rsi+0000000000001200h]
  000000014032F6E7: test        rdx,rdx
  000000014032F6EA: je          000000014032F704
  000000014032F6EC: mov         dword ptr [rsp+28h],ebx
  000000014032F6F0: mov         r9d,dword ptr [r14+4]
  000000014032F6F4: mov         rcx,r12
  000000014032F6F7: mov         r8d,dword ptr [r14]
  000000014032F6FA: mov         dword ptr [rsp+20h],r15d
  000000014032F6FF: call        000000014029E260
  000000014032F704: mov         rcx,qword ptr [rbp-51h]
  000000014032F708: mov         r9d,edi
  000000014032F70B: mov         r8d,dword ptr [rbp-55h]
  000000014032F70F: mov         edx,dword ptr [rbp-59h]
  000000014032F712: sub         r8d,edi
  000000014032F715: mov         dword ptr [rsp+38h],r15d
  000000014032F71A: mov         eax,dword ptr [rcx]
  000000014032F71C: mov         dword ptr [rbp-19h],eax
  000000014032F71F: mov         eax,dword ptr [rcx+4]
  000000014032F722: sub         eax,edi
  000000014032F724: mov         dword ptr [rbp-15h],eax
  000000014032F727: mov         eax,dword ptr [rcx+8]
  000000014032F72A: mov         dword ptr [rbp-11h],eax
  000000014032F72D: mov         eax,dword ptr [rcx+0Ch]
  000000014032F730: mov         rcx,r12
  000000014032F733: sub         eax,edi
  000000014032F735: mov         dword ptr [rbp-0Dh],eax
  000000014032F738: movzx       eax,byte ptr [rbp+000000000000008Fh]
  000000014032F73F: mov         byte ptr [rsp+30h],al
  000000014032F743: lea         rax,[rbp-19h]
  000000014032F747: mov         qword ptr [rsp+28h],rax
  000000014032F74C: mov         qword ptr [rsp+20h],r14
  000000014032F751: call        000000014029E4C0
  000000014032F756: cmp         dword ptr [rbp+0000000000000097h],0
  000000014032F75D: lea         r9,[rbp-51h]
  000000014032F761: mov         rbx,qword ptr [rsp+00000000000000F0h]
  000000014032F769: mov         edx,r15d
  000000014032F76C: je          000000014032F78C
  000000014032F76E: mov         ecx,dword ptr [r14]
  000000014032F771: lea         r8,[rbp-29h]
  000000014032F775: add         ecx,dword ptr [rbp-59h]
  000000014032F778: mov         rax,qword ptr [rbp-59h]
  000000014032F77C: shr         rax,20h
  000000014032F780: add         eax,dword ptr [r14+4]
  000000014032F784: mov         dword ptr [rbp-4Dh],eax
  000000014032F787: mov         dword ptr [rbp-51h],ecx
  000000014032F78A: jmp         000000014032F795
  000000014032F78C: xor         eax,eax
  000000014032F78E: mov         qword ptr [rbp-51h],rax
  000000014032F792: xor         r8d,r8d
  000000014032F795: mov         rcx,r12
  000000014032F798: call        000000014029EA40
  000000014032F79D: movaps      xmm0,xmmword ptr [rbp-29h]
  000000014032F7A1: lea         rcx,[rbp-39h]
  000000014032F7A5: xor         r8d,r8d
  000000014032F7A8: movdqa      xmmword ptr [rbp-39h],xmm0
  000000014032F7AD: xor         edx,edx
  000000014032F7AF: cmp         byte ptr [rsi+20h],dl
  000000014032F7B2: je          000000014032F7D7
  000000014032F7B4: lea         r9d,[r8+5]
  000000014032F7B8: mov         dword ptr [rsp+20h],5
  000000014032F7C0: call        0000000140407B20
  000000014032F7C5: add         dword ptr [rbp-39h],2
  000000014032F7C9: add         dword ptr [rbp-31h],2
  000000014032F7CD: add         dword ptr [rbp-35h],2
  000000014032F7D1: add         dword ptr [rbp-2Dh],2
  000000014032F7D5: jmp         000000014032F7F6
  000000014032F7D7: mov         r9d,2
  000000014032F7DD: mov         dword ptr [rsp+20h],2
  000000014032F7E5: call        0000000140407B20
  000000014032F7EA: inc         dword ptr [rbp-39h]
  000000014032F7ED: inc         dword ptr [rbp-31h]
  000000014032F7F0: inc         dword ptr [rbp-35h]
  000000014032F7F3: inc         dword ptr [rbp-2Dh]
  000000014032F7F6: cmp         byte ptr [rsi+20h],0
  000000014032F7FA: je          000000014032F828
  000000014032F7FC: mov         ecx,r15d
  000000014032F7FF: and         ecx,10000000h
  000000014032F805: or          ecx,28000000h
  000000014032F80B: shr         ecx,1Bh
  000000014032F80E: call        0000000140413220
  000000014032F813: mov         rdx,qword ptr [rbp-49h]
  000000014032F817: mov         rcx,rsi
  000000014032F81A: call        0000000140329120
  000000014032F81F: mov         ecx,eax
  000000014032F821: call        0000000140413200
  000000014032F826: jmp         000000014032F82F
  000000014032F828: xor         ecx,ecx
  000000014032F82A: call        0000000140413220
  000000014032F82F: movaps      xmm0,xmmword ptr [rbp-39h]
  000000014032F833: lea         rax,[rbp-49h]
  000000014032F837: mov         r9d,dword ptr [rbp-55h]
  000000014032F83B: lea         rdx,[rbp-29h]
  000000014032F83F: mov         r8d,dword ptr [rbp-59h]
  000000014032F843: mov         rcx,r12
  000000014032F846: mov         qword ptr [rsp+38h],rax
  000000014032F84B: mov         eax,dword ptr [r14+4]
  000000014032F84F: mov         dword ptr [rsp+30h],r15d
  000000014032F854: mov         dword ptr [rsp+28h],eax
  000000014032F858: mov         eax,dword ptr [r14]
  000000014032F85B: mov         dword ptr [rsp+20h],eax
  000000014032F85F: movdqa      xmmword ptr [rbp-49h],xmm0
  000000014032F864: call        000000014029DFF0
  000000014032F869: xor         ecx,ecx
  000000014032F86B: call        0000000140413220
  000000014032F870: mov         rcx,qword ptr [rbp-9]
  000000014032F874: xor         rcx,rsp
  000000014032F877: call        00000001404F77A0
  000000014032F87C: add         rsp,0A0h
  000000014032F883: pop         r15
  000000014032F885: pop         r14
  000000014032F887: pop         r13
  000000014032F889: pop         r12
  000000014032F88B: pop         rdi
  000000014032F88C: pop         rsi
  000000014032F88D: pop         rbp
  000000014032F88E: ret
  000000014032F88F: nop
  000000014032F890: jle         000000014032F887
  000000014032F892: xor         al,byte ptr [rax]
  000000014032F894: jle         000000014032F88B
  000000014032F896: xor         al,byte ptr [rax]
  000000014032F898: jle         000000014032F88F
  000000014032F89A: xor         al,byte ptr [rax]
  000000014032F89C: mov         bl,0F5h
  000000014032F89E: xor         al,byte ptr [rax]
  000000014032F8A0: mov         bl,0F5h
  000000014032F8A2: xor         al,byte ptr [rax]
  000000014032F8A4: mov         bl,0F5h
  000000014032F8A6: xor         al,byte ptr [rax]
  000000014032F8A8: mov         bl,0F5h
  000000014032F8AA: xor         al,byte ptr [rax]
  000000014032F8AC: mov         bl,0F5h
  000000014032F8AE: xor         al,byte ptr [rax]
  000000014032F8B0: 2F
  000000014032F8B1: div         al,byte ptr [rdx]
  000000014032F8B3: add         byte ptr [rcx-0Ah],dh
  000000014032F8B6: xor         al,byte ptr [rax]
  000000014032F8B8: jno         000000014032F8B0
  000000014032F8BA: xor         al,byte ptr [rax]
  000000014032F8BC: jno         000000014032F8B4
  000000014032F8BE: xor         al,byte ptr [rax]
  000000014032F8C0: jno         000000014032F8B8
  000000014032F8C2: xor         al,byte ptr [rax]
  000000014032F8C4: jno         000000014032F8BC
  000000014032F8C6: xor         al,byte ptr [rax]
  000000014032F8C8: jno         000000014032F8C0
  000000014032F8CA: xor         al,byte ptr [rax]
  000000014032F8CC: jno         000000014032F8C4
  000000014032F8CE: xor         al,byte ptr [rax]
  000000014032F8D0: 40

  Summary

      589000 .text
