vim.loader.enable()

vim.g.mapleader = " "
vim.g.maplocalleader = "\\"

require("options")
require("plugins")
require("keymaps")
require("autocmds")
