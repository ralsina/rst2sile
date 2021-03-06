SILE.registerCommand("relindent", function(options, content)
    if options["left"] then
        local lskip = SILE.settings.get("document.lskip") or SILE.nodefactory.newGlue('0pt')
        local indent = SILE.nodefactory.newGlue(tostring(lskip['width'] + SILE.length.parse(options["left"])))
        SILE.settings.set("document.lskip", indent)
    end
    if options["right"] then
        local rskip = SILE.settings.get("document.rskip") or SILE.nodefactory.newGlue('0pt')
        local indent = SILE.nodefactory.newGlue(tostring(rskip['width'] + SILE.length.parse(options["right"])))
        SILE.settings.set("document.rskip", indent)
    end
    SILE.process(content)
    if options["left"] then
        SILE.settings.set("document.lskip", lskip)
    end
    if options["right"] then
        SILE.settings.set("document.rskip", rskip)
    end
end)

-- SILE.require('packages/rebox')
-- SILE.registerCommand("bullet", function(options, content)
--     SILE.call("rebox", {width = '0mm'}, {"*"})
-- end)
