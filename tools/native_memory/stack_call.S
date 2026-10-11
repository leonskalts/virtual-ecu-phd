/* x86-64 SysV only. Separate measurement stack, production code unchanged. */
.text
.globl stack_call
.type stack_call,@function
stack_call:
 push %r12
 mov %rsp,%r12
 mov %rdi,%rsp
 and $-16,%rsp
 mov %rsi,%rax
 mov %rdx,%rdi
 mov %rcx,%rsi
 mov %r8,%rdx
 call *%rax
 mov %r12,%rsp
 pop %r12
 ret
.size stack_call,.-stack_call
.section .note.GNU-stack,"",@progbits
