local vscode = vim.g.vscode ~= nil
local pack_root = vim.fn.stdpath("data") .. "/site/pack/plugins"
local opt_path = pack_root .. "/opt"
local start_path = pack_root .. "/start"

-- vscode = true: useful inside vscode-neovim / Cursor (motions, textobjects).
-- Everything else stays available for standalone Neovim only.
local plugins = {
  ["99"] = { url = "https://github.com/ThePrimeagen/99.git" },
  ["blink-cmp-supermaven"] = { url = "https://github.com/Huijiro/blink-cmp-supermaven.git" },
  ["blink.cmp"] = { url = "https://github.com/saghen/blink.cmp.git" },
  ["blink.compat"] = { url = "https://github.com/saghen/blink.compat.git" },
  ["blink.lib"] = { url = "https://github.com/saghen/blink.lib.git" },
  ["catppuccin"] = { url = "https://github.com/catppuccin/nvim.git" },
  ["conform.nvim"] = { url = "https://github.com/stevearc/conform.nvim.git" },
  ["diffview.nvim"] = { url = "https://github.com/sindrets/diffview.nvim.git" },
  ["gitsigns.nvim"] = { url = "https://github.com/lewis6991/gitsigns.nvim.git" },
  ["leap.nvim"] = { url = "https://codeberg.org/andyg/leap.nvim.git", vscode = true },
  ["lualine.nvim"] = { url = "https://github.com/nvim-lualine/lualine.nvim.git" },
  ["mini.pairs"] = { url = "https://github.com/echasnovski/mini.pairs.git" },
  ["mini.surround"] = { url = "https://github.com/echasnovski/mini.surround.git", vscode = true },
  ["nvim-treesitter"] = { url = "https://github.com/nvim-treesitter/nvim-treesitter.git", vscode = true },
  ["nvim-treesitter-textobjects"] = {
    url = "https://github.com/nvim-treesitter/nvim-treesitter-textobjects.git",
    vscode = true,
  },
  ["nvim-web-devicons"] = { url = "https://github.com/nvim-tree/nvim-web-devicons.git" },
  ["obsidian-bridge.nvim"] = { url = "https://github.com/oflisback/obsidian-bridge.nvim.git" },
  ["obsidian.nvim"] = { url = "https://github.com/epwalsh/obsidian.nvim.git" },
  ["oil.nvim"] = { url = "https://github.com/stevearc/oil.nvim.git" },
  ["plenary.nvim"] = { url = "https://github.com/nvim-lua/plenary.nvim.git" },
  ["supermaven"] = { url = "https://github.com/supermaven-inc/supermaven-nvim.git" },
  ["telescope-undo.nvim"] = { url = "https://github.com/debugloop/telescope-undo.nvim.git" },
  ["telescope-fzf-native.nvim"] = { url = "https://github.com/nvim-telescope/telescope-fzf-native.nvim.git" },
  ["telescope.nvim"] = { url = "https://github.com/nvim-telescope/telescope.nvim.git" },
  ["trouble.nvim"] = { url = "https://github.com/folke/trouble.nvim.git" },
  ["vim-repeat"] = { url = "https://github.com/tpope/vim-repeat.git", vscode = true },
  ["which-key.nvim"] = { url = "https://github.com/folke/which-key.nvim.git" },
}

local function plugin_enabled(spec)
  return not vscode or spec.vscode
end

-- Prefer opt/ so vscode can skip packadd for host-owned features.
-- Migrate leftovers from the old start/ layout.
local function plugin_dir(name)
  return opt_path .. "/" .. name
end

local function migrate_from_start(name)
  local old = start_path .. "/" .. name
  local new = plugin_dir(name)
  if vim.uv.fs_stat(old) and not vim.uv.fs_stat(new) then
    vim.fn.mkdir(opt_path, "p")
    vim.fn.rename(old, new)
  end
end

local function bootstrap()
  vim.fn.mkdir(opt_path, "p")
  local missing = {}
  for name, spec in pairs(plugins) do
    migrate_from_start(name)
    local dir = plugin_dir(name)
    if not vim.uv.fs_stat(dir) then
      table.insert(missing, name)
      vim.fn.system({ "git", "clone", "--filter=blob:none", spec.url, dir })
    end
  end
  if #missing > 0 then
    vim.notify("Installed: " .. table.concat(missing, ", "), vim.log.levels.INFO)
    vim.cmd("helptags ALL")
    return true
  end
  return false
end

local did_bootstrap = bootstrap()

-- Build telescope-fzf-native only for standalone Neovim
local fzf_dir = plugin_dir("telescope-fzf-native.nvim")
if not vscode
  and vim.uv.fs_stat(fzf_dir)
  and not vim.uv.fs_stat(fzf_dir .. "/build/libfzf.so")
  and not vim.uv.fs_stat(fzf_dir .. "/build/libfzf.dylib")
then
  vim.fn.system({ "make", "-C", fzf_dir })
end

-- Deterministic order so deps (e.g. blink.lib) load before dependents
local names = {}
for name in pairs(plugins) do
  table.insert(names, name)
end
local priority = {
  ["blink.lib"] = 1,
  ["blink.compat"] = 2,
  ["plenary.nvim"] = 3,
  ["nvim-treesitter"] = 4,
  ["nvim-web-devicons"] = 5,
}
table.sort(names, function(a, b)
  local pa, pb = priority[a] or 100, priority[b] or 100
  if pa ~= pb then
    return pa < pb
  end
  return a < b
end)

for _, name in ipairs(names) do
  if plugin_enabled(plugins[name]) then
    vim.cmd.packadd(name)
  end
end

if not vscode and did_bootstrap then
  require("blink.cmp").build():pwait()
end

if vscode then
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
require("plugins.gitsigns")
require("plugins.misc")
require("plugins.lualine")
require("plugins.oil")
require("plugins.99")
require("plugins.obsidian")
require("plugins.obsidian-bridge")
