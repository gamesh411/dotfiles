local pack_path = vim.fn.stdpath("data") .. "/site/pack/plugins/start"

local plugins = {
  ["99"] = "https://github.com/ThePrimeagen/99.git",
  ["blink-cmp-supermaven"] = "https://github.com/Huijiro/blink-cmp-supermaven.git",
  ["blink.cmp"] = "https://github.com/saghen/blink.cmp.git",
  ["blink.compat"] = "https://github.com/saghen/blink.compat.git",
  ["blink.lib"] = "https://github.com/saghen/blink.lib.git",
  ["catppuccin"] = "https://github.com/catppuccin/nvim.git",
  ["conform.nvim"] = "https://github.com/stevearc/conform.nvim.git",
  ["gitsigns.nvim"] = "https://github.com/lewis6991/gitsigns.nvim.git",
  ["leap.nvim"] = "https://codeberg.org/andyg/leap.nvim.git",
  ["lualine.nvim"] = "https://github.com/nvim-lualine/lualine.nvim.git",
  ["mini.pairs"] = "https://github.com/echasnovski/mini.pairs.git",
  ["mini.surround"] = "https://github.com/echasnovski/mini.surround.git",
  ["nvim-lspconfig"] = "https://github.com/neovim/nvim-lspconfig.git",
  ["nvim-treesitter"] = "https://github.com/nvim-treesitter/nvim-treesitter.git",
  ["nvim-treesitter-textobjects"] = "https://github.com/nvim-treesitter/nvim-treesitter-textobjects.git",
  ["nvim-web-devicons"] = "https://github.com/nvim-tree/nvim-web-devicons.git",
  ["obsidian-bridge.nvim"] = "https://github.com/oflisback/obsidian-bridge.nvim.git",
  ["obsidian.nvim"] = "https://github.com/epwalsh/obsidian.nvim.git",
  ["oil.nvim"] = "https://github.com/stevearc/oil.nvim.git",
  ["plenary.nvim"] = "https://github.com/nvim-lua/plenary.nvim.git",
  ["supermaven"] = "https://github.com/supermaven-inc/supermaven-nvim.git",
  ["telescope-undo.nvim"] = "https://github.com/debugloop/telescope-undo.nvim.git",
  ["telescope.nvim"] = "https://github.com/nvim-telescope/telescope.nvim.git",
  ["trouble.nvim"] = "https://github.com/folke/trouble.nvim.git",
  ["vim-repeat"] = "https://github.com/tpope/vim-repeat.git",
  ["which-key.nvim"] = "https://github.com/folke/which-key.nvim.git",
}

-- Bootstrap: clone missing plugins
local function bootstrap()
  vim.fn.mkdir(pack_path, "p")
  local missing = {}
  for name, url in pairs(plugins) do
    local dir = pack_path .. "/" .. name
    if not vim.uv.fs_stat(dir) then
      table.insert(missing, name)
      vim.fn.system({ "git", "clone", "--filter=blob:none", url, dir })
    end
  end
  if #missing > 0 then
    vim.notify("Installed: " .. table.concat(missing, ", "), vim.log.levels.INFO)
    vim.cmd("packloadall")
    vim.cmd("helptags ALL")
    -- blink.cmp needs native library built after clone
    require("blink.cmp").build():pwait()
  end
end

bootstrap()

-- Load plugin configs
require("plugins.treesitter")
require("plugins.leap")
require("plugins.telescope")
require("plugins.lsp")
require("plugins.conform")
require("plugins.supermaven")
require("plugins.blink")
require("plugins.gitsigns")
require("plugins.misc")
require("plugins.lualine")
require("plugins.oil")
require("plugins.99")
require("plugins.obsidian")
require("plugins.obsidian-bridge")
