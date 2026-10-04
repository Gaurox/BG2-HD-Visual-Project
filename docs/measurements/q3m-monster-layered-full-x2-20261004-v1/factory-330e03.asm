Microsoft (R) COFF/PE Dumper Version 14.29.30158.0
Copyright (C) Microsoft Corporation.  All rights reserved.


Dump of file G:\SteamLibrary\steamapps\common\Baldur's Gate II Enhanced Edition\BaldurReal.exe

File Type: EXECUTABLE IMAGE

  0000000140330D9F: add         byte ptr [rbx+rcx*4-31h],al
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

  Summary

      589000 .text
