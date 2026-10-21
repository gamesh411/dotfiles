local in_vscode = vim.fn.exists('g:vscode') == 1

if (not in_vscode) then
    vim.pack.add {
        "https://github.com/ThePrimeagen/99.git",
        "https://github.com/Huijiro/blink-cmp-supermaven.git",
        "https://github.com/saghen/blink.cmp.git",
        "https://github.com/saghen/blink.compat.git",
        "https://github.com/saghen/blink.lib.git",
        "https://github.com/catppuccin/nvim.git",
        "https://github.com/stevearc/conform.nvim.git",
        "https://github.com/sindrets/diffview.nvim.git",
        "https://github.com/lewis6991/gitsigns.nvim.git",
        "https://github.com/nvim-lualine/lualine.nvim.git",
        "https://github.com/echasnovski/mini.pairs.git",
        "https://github.com/nvim-tree/nvim-web-devicons.git",
        "https://github.com/oflisback/obsidian-bridge.nvim.git",
        "https://github.com/epwalsh/obsidian.nvim.git",
        "https://github.com/stevearc/oil.nvim.git",
        "https://github.com/nvim-lua/plenary.nvim.git",
        "https://github.com/supermaven-inc/supermaven-nvim.git",
        "https://github.com/debugloop/telescope-undo.nvim.git",
        "https://github.com/nvim-telescope/telescope-fzf-native.nvim.git",
        "https://github.com/nvim-telescope/telescope.nvim.git",
        "https://github.com/folke/trouble.nvim.git",
    }
end

vim.pack.add {
    "https://github.com/tpope/vim-repeat.git",
    "https://github.com/folke/which-key.nvim.git",
    "https://github.com/echasnovski/mini.surround.git",
    "https://github.com/nvim-treesitter/nvim-treesitter.git",
    "https://github.com/nvim-treesitter/nvim-treesitter-textobjects.git",
    "https://codeberg.org/andyg/leap.nvim.git",
}

if in_vscode then
    require("plugins.treesitter")
    require("plugins.leap")
    require("mini.surround").setup({})
    return
end

require("plugins.treesitter")
require("plugins.leap")
require("plugins.telescope")
require("plugins.lsp")
require("plugins.conform")
require("plugins.supermaven")
require("plugins.blink")
local cmp = require('blink.cmp')
cmp.build():pwait()
cmp.setup()
require("plugins.gitsigns")
require("plugins.misc")
require("plugins.lualine")
require("plugins.oil")
require("plugins.99")
require("plugins.obsidian")
require("plugins.obsidian-bridge")
