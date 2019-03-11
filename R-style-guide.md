# PIH R Style Guide

Follow the
[Google Style Guide](https://google.github.io/styleguide/Rguide.xml).
This document should be read as an extension of that, with the following
exception:

Curly braces are obligatory for all blocks, even single-line blocks.
Inline blocks are acceptable, but use them sparingly. A good use is an
inline `if/else` statement in the style of other languages' ternary 
operator. You may omit curly braces for inline blocks.

```
if (is.null(ylim)) {
  ylim <- c(0, 0.06)
}
```

```
if (x > 5) "yes" else "no"
```

BAD: 
```
if (is.null(ylim))
  ylim <- c(0, 0.06) 
```



## Packrat

Use [prackrat](https://rstudio.github.io/packrat/)
for dependency management. Be sure to execute
`packrat::set_opts(vcs.ignore.src = TRUE)`
so that it adds `packrat/src` to your `.gitignore`, so that you aren't
committing your depedencies themselves to VCS.

