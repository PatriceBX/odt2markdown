odt2markdown
============

A converter from Open Document ODT format to markdown.    
Could be called odt2text, similar to aaronsw's html2text.   
If someone is interrested, let me know, I might work on it some more !

It reads from an odt document using the (almost totally undocumented) odfpy package.

Goes through all text in the doc and interprets the following formatting: 

- bold
- italic
- courrier font  ->  means code
- lists

This is all converted into markdown syntax, so that it can easily be inserted into an html page, 
using a markdown filter, of which many exist.    Markdown is also easily editable in a simple textarea field.

For now it does not handle Header 1/2/3 styles, but it would be quite easy to add.
