Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  0000000140330D80: mov         qword ptr [rsp+8],rbx
  0000000140330D85: mov         qword ptr [rsp+10h],rsi
  0000000140330D8A: push        rdi
  0000000140330D8B: sub         rsp,20h
  0000000140330D8F: movzx       edi,cx
  0000000140330D92: movzx       ebx,r8w
  0000000140330D96: mov         eax,edi
  0000000140330D98: mov         rsi,rdx
  0000000140330D9B: and         eax,0F000h
  0000000140330DA0: mov         r9d,edi
  0000000140330DA3: cmp         eax,7000h
  0000000140330DA8: ja          000000014033121A
  0000000140330DAE: je          00000001403310BC
  0000000140330DB4: cmp         eax,3000h
  0000000140330DB9: ja          0000000140330F23
  0000000140330DBF: je          0000000140330EF2
  0000000140330DC5: test        eax,eax
  0000000140330DC7: je          0000000140330EC1
  0000000140330DCD: cmp         eax,1000h
  0000000140330DD2: je          0000000140330E10
  0000000140330DD4: cmp         eax,2000h
  0000000140330DD9: jne         000000014033131D
  0000000140330DDF: mov         ecx,1760h
  0000000140330DE4: call        00000001404F7A88
  0000000140330DE9: test        rax,rax
  0000000140330DEC: je          00000001403313AD
  0000000140330DF2: and         bx,0Fh
  0000000140330DF6: mov         r8,rsi
  0000000140330DF9: movzx       r9d,bx
  0000000140330DFD: movzx       edx,di
  0000000140330E00: mov         rcx,rax
  0000000140330E03: call        00000001403119A0
  0000000140330E08: mov         rbx,rax
  0000000140330E0B: jmp         00000001403313AF
  0000000140330E10: test        r9d,0E00h
  0000000140330E17: je          0000000140330E90
  0000000140330E19: mov         edx,0F00h
  0000000140330E1E: movzx       eax,di
  0000000140330E21: and         ax,dx
  0000000140330E24: mov         edx,300h
  0000000140330E29: cmp         ax,dx
  0000000140330E2C: jne         0000000140330E5F
  0000000140330E2E: mov         ecx,0D60h
  0000000140330E33: call        00000001404F7A88
  0000000140330E38: test        rax,rax
  0000000140330E3B: je          00000001403313AD
  0000000140330E41: and         bx,0Fh
  0000000140330E45: mov         r8,rsi
  0000000140330E48: movzx       r9d,bx
  0000000140330E4C: movzx       edx,di
  0000000140330E4F: mov         rcx,rax
  0000000140330E52: call        0000000140312EE0
  0000000140330E57: mov         rbx,rax
  0000000140330E5A: jmp         00000001403313AF
  0000000140330E5F: mov         ecx,1308h
  0000000140330E64: call        00000001404F7A88
  0000000140330E69: test        rax,rax
  0000000140330E6C: je          00000001403313AD
  0000000140330E72: and         bx,0Fh
  0000000140330E76: mov         r8,rsi
  0000000140330E79: movzx       r9d,bx
  0000000140330E7D: movzx       edx,di
  0000000140330E80: mov         rcx,rax
  0000000140330E83: call        00000001403120D0
  0000000140330E88: mov         rbx,rax
  0000000140330E8B: jmp         00000001403313AF
  0000000140330E90: mov         ecx,0D68h
  0000000140330E95: call        00000001404F7A88
  0000000140330E9A: test        rax,rax
  0000000140330E9D: je          00000001403313AD
  0000000140330EA3: and         bx,0Fh
  0000000140330EA7: mov         r8,rsi
  0000000140330EAA: movzx       r9d,bx
  0000000140330EAE: movzx       edx,di
  0000000140330EB1: mov         rcx,rax
  0000000140330EB4: call        0000000140314350
  0000000140330EB9: mov         rbx,rax
  0000000140330EBC: jmp         00000001403313AF
  0000000140330EC1: B9

  Summary

      589000 .text
