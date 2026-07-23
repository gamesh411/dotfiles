-- Colorscheme (load first)
require("catppuccin").setup({
  flavour = "latte",
})
vim.cmd.colorscheme("catppuccin")

-- Which-key
local wk = require("which-key")
wk.setup({})
wk.add({
  { "<leader>f", group = "Find" },
  { "<leader>x", group = "Trouble" },
  { "<leader>s", group = "Session" },
  { "<leader>g", group = "Git" },
  { "<leader>gd", group = "Diffview" },
  { "<leader>c", group = "Code" },
  { "<leader>o", group = "Obsidian" },
  { "<leader>t", group = "Terminal" },
  { "<leader>,", group = "Config" },
  { "<leader>b", group = "Buffer" },
  { "<leader>a", group = "Auto" },
})

-- Mini.surround
require("mini.surround").setup({})

-- Mini.pairs
require("mini.pairs").setup({})

-- Trouble
local trouble = require("trouble")
trouble.setup({})
vim.keymap.set("n", "<leader>xx", function() trouble.toggle("diagnostics") end, { desc = "Diagnostics (Trouble)" })
vim.keymap.set("n", "<leader>xd", function() trouble.toggle({ mode = "diagnostics", filter = { buf = 0 } }) end, { desc = "Buffer diagnostics (Trouble)" })
vim.keymap.set("n", "<leader>xe", function() trouble.toggle({ mode = "diagnostics", filter = { severity = vim.diagnostic.severity.ERROR } }) end, { desc = "Errors only (Trouble)" })
vim.keymap.set("n", "<leader>xs", function() trouble.toggle("symbols") end, { desc = "Symbols (Trouble)" })
vim.keymap.set("n", "<leader>xq", function() trouble.toggle("quickfix") end, { desc = "Quickfix (Trouble)" })
vim.keymap.set("n", "<leader>xl", function() trouble.toggle("loclist") end, { desc = "Loclist (Trouble)" })

-- Diffview
require("diffview").setup({})
vim.keymap.set("n", "<leader>gdo", "<cmd>DiffviewOpen<cr>", { desc = "Open diffview" })
vim.keymap.set("n", "<leader>gdc", "<cmd>DiffviewClose<cr>", { desc = "Close diffview" })
vim.keymap.set("n", "<leader>gdh", "<cmd>DiffviewFileHistory %<cr>", { desc = "File history" })
vim.keymap.set("n", "<leader>gdH", "<cmd>DiffviewFileHistory<cr>", { desc = "Branch history" })