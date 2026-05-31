" Vim syntax file
" Language:    Glossolalia (.glo) — utterance is execution
" Maintainer:  noisyloop
" URL:         https://github.com/noisyloop/glossolalia

if exists("b:current_syntax")
  finish
endif

" Comments — a ~ to end of line
syn match   gloComment      "\~.*$"

" Glyphs (strings) with escapes
syn region  gloString       start=+"+ skip=+\\"+ end=+"+ contains=gloEscape
syn match   gloEscape       contained "\\[nt\"\\]"

" Numbers: tone (float) and pulse (int)
syn match   gloTone         "\<-\=\d\+\.\d\+\>"
syn match   gloPulse        "\<-\=\d\+\>"

" Literals
syn keyword gloConstant     true false void

" Commands (things that do)
syn keyword gloCommand      speak hush burn rise fall drift breathe silence
syn keyword gloCommand      open close channel send sync voices chant
syn keyword gloCommand      remember forget

" Block / definition keywords
syn keyword gloBlock        incant voice ritual invoke call takes end
syn keyword gloBlock        nextgroup=gloFuncName skipwhite

" Control flow
syn keyword gloControl      if else repeat until in echo

" Comparison & logic operators
syn keyword gloOperator     is not above below and or

" Arithmetic & tone-craft operators
syn keyword gloOperator     add subtract scale modulate ascend descend

" Strand & glyph craft
syn keyword gloOperator     weave unweave count at fracture converge

" Types
syn keyword gloType         tone pulse glyph flicker sigil

" Structure words
syn keyword gloStructure    let be set to by with for as

" Name following a definition keyword
syn match   gloFuncName     contained "\<[A-Za-z_][A-Za-z0-9_]*\>"

hi def link gloComment      Comment
hi def link gloString       String
hi def link gloEscape       SpecialChar
hi def link gloTone         Float
hi def link gloPulse        Number
hi def link gloConstant     Constant
hi def link gloCommand      Function
hi def link gloBlock        Keyword
hi def link gloControl      Conditional
hi def link gloOperator     Operator
hi def link gloType         Type
hi def link gloStructure    Statement
hi def link gloFuncName     Identifier

let b:current_syntax = "glossolalia"
