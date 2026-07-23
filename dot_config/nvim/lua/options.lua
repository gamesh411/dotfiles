vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.signcolumn = "yes"
vim.opt.cursorline = true

vim.opt.tabstop = 4
vim.opt.shiftwidth = 4
vim.opt.expandtab = true
vim.opt.smartindent = true

vim.opt.splitright = true
vim.opt.splitbelow = true
vim.opt.splitkeep = "screen"

vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.inccommand = "split"
vim.opt.grepprg = "rg --vimgrep"
vim.opt.grepformat = "%f:%l:%c:%m"

vim.opt.undofile = true
vim.opt.swapfile = false
vim.opt.clipboard = "unnamedplus"

vim.opt.termguicolors = true
vim.opt.winbar = "%=%m %f"
vim.opt.exrc = true
vim.opt.scrolloff = 8

vim.opt.conceallevel = 2

vim.opt.updatetime = 250
vim.opt.timeoutlen = 400

vim.diagnostic.config({
  virtual_text = { spacing = 4, prefix = "●" },
  signs = true,
  underline = true,
  update_in_insert = false,
  severity_sort = true,
})