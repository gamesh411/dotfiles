require("nvim-treesitter").setup({})

-- Install parsers if missing
local parsers = { "c", "cpp", "python", "lua", "vim", "vimdoc", "query", "markdown", "markdown_inline", "bash" }
local installed = require("nvim-treesitter").get_installed()
local installed_set = {}
for _, p in ipairs(installed) do
  installed_set[p] = true
end
local to_install = {}
for _, p in ipairs(parsers) do
  if not installed_set[p] then
    table.insert(to_install, p)
  end
end
if #to_install > 0 then
  require("nvim-treesitter").install(to_install)
end

-- Highlighting is owned by VS Code / Cursor when embedded
if not vim.g.vscode then
  vim.api.nvim_create_autocmd("FileType", {
    group = vim.api.nvim_create_augroup("TreesitterHighlight", {}),
    callback = function()
      pcall(vim.treesitter.start)
    end,
  })
end

-- Treesitter textobjects
require("nvim-treesitter-textobjects").setup()

local map = vim.keymap.set

-- Textobject select
local select_map = function(lhs, query, desc)
  map({ "x", "o" }, lhs, function()
    require("nvim-treesitter-textobjects.select").select_textobject(query, "textobjects")
  end, { desc = desc })
end

select_map("af", "@function.outer", "Around function")
select_map("if", "@function.inner", "Inside function")
select_map("ac", "@class.outer", "Around class")
select_map("ic", "@class.inner", "Inside class")
select_map("aa", "@parameter.outer", "Around argument")
select_map("ia", "@parameter.inner", "Inside argument")
select_map("ai", "@conditional.outer", "Around conditional")
select_map("ii", "@conditional.inner", "Inside conditional")
select_map("al", "@loop.outer", "Around loop")
select_map("il", "@loop.inner", "Inside loop")

-- Goto next/prev start of function/class
local goto_map = function(lhs, query, backward, desc)
  map({ "n", "x", "o" }, lhs, function()
    require("nvim-treesitter-textobjects.move").goto_next_start(query, "textobjects", backward)
  end, { desc = desc })
end

goto_map("]f", "@function.outer", false, "Next function")
goto_map("[f", "@function.outer", true, "Prev function")
goto_map("]c", "@class.outer", false, "Next class")
goto_map("[c", "@class.outer", true, "Prev class")
goto_map("]a", "@parameter.outer", false, "Next argument")
goto_map("[a", "@parameter.outer", true, "Prev argument")
