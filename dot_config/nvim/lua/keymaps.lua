local map = vim.keymap.set

-- window navigation
map("n", "<C-h>", "<C-w>h", { desc = "Window left" })
map("n", "<C-j>", "<C-w>j", { desc = "Window down" })
map("n", "<C-k>", "<C-w>k", { desc = "Window up" })
map("n", "<C-l>", "<C-w>l", { desc = "Window right" })

-- resize with arrows
map("n", "<C-S-k>", "<cmd>resize +3<cr>", { desc = "Resize up" })
map("n", "<C-S-j>", "<cmd>resize -3<cr>", { desc = "Resize down" })
map("n", "<C-S-h>", "<cmd>vertical resize -3<cr>", { desc = "Resize left" })
map("n", "<C-S-l>", "<cmd>vertical resize +3<cr>", { desc = "Resize right" })

-- move lines
map("v", "K", ":m '<-2<cr>gv=gv", { silent = true, desc = "Move selection up" })
map("v", "J", ":m '>+1<cr>gv=gv", { silent = true, desc = "Move selection down" })

-- keep cursor centered
map("n", "<C-d>", "<C-d>zz", { desc = "Scroll down (centered)" })
map("n", "<C-u>", "<C-u>zz", { desc = "Scroll up (centered)" })
map("n", "n", "nzzzv", { desc = "Next match (centered)" })
map("n", "N", "Nzzzv", { desc = "Prev match (centered)" })

-- paste without losing register
map("x", "<leader>p", [["_dP]], { desc = "Paste (keep register)" })

-- yank to system clipboard
map({ "n", "v" }, "<leader>y", [["+y]], { desc = "Yank to clipboard" })
map("n", "<leader>Y", [["+Y]], { desc = "Yank line to clipboard" })

-- clear search highlight
map("n", "<Esc>", "<cmd>nohlsearch<cr>", { desc = "Clear search highlight" })

-- quickfix navigation
map("n", "]q", "<cmd>cnext<cr>zz", { desc = "Next quickfix" })
map("n", "[q", "<cmd>cprev<cr>zz", { desc = "Prev quickfix" })

-- buffer navigation
map("n", "]b", "<cmd>bnext<cr>", { desc = "Next buffer" })
map("n", "[b", "<cmd>bprev<cr>", { desc = "Prev buffer" })
map("n", "<leader>bd", "<cmd>bdelete<cr>", { desc = "Delete buffer" })

-- diagnostic navigation (global, works without LSP)
map("n", "]d", function() vim.diagnostic.jump({ count = 1 }) end, { desc = "Next diagnostic" })
map("n", "[d", function() vim.diagnostic.jump({ count = -1 }) end, { desc = "Prev diagnostic" })

-- enter command mode faster
map({ "n", "v" }, ";", ":", { desc = "Command mode" })

-- terminal
map("n", "<leader>tv", "<cmd>vsplit | terminal<cr>", { desc = "Terminal (vertical)" })
map("n", "<leader>th", "<cmd>split | terminal<cr>", { desc = "Terminal (horizontal)" })
map("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Exit terminal mode" })
map("t", "<C-h>", "<cmd>wincmd h<cr>", { desc = "Window left" })
map("t", "<C-j>", "<cmd>wincmd j<cr>", { desc = "Window down" })
map("t", "<C-k>", "<cmd>wincmd k<cr>", { desc = "Window up" })
map("t", "<C-l>", "<cmd>wincmd l<cr>", { desc = "Window right" })

-- config management (<leader>,)
map("n", "<leader>,s", "<cmd>source %<cr>", { desc = "Source current file" })
map("n", "<leader>,t", function()
  vim.secure.trust({ action = "allow", path = vim.fn.expand("%:p") })
  vim.notify("Trusted: " .. vim.fn.expand("%:p"))
end, { desc = "Trust current file" })
map("n", "<leader>,r", function()
  vim.loader.reset()
  for _, mod in ipairs({ "options", "keymaps", "autocmds" }) do
    package.loaded[mod] = nil
    require(mod)
  end
  vim.notify("Config reloaded (options/keymaps/autocmds)")
end, { desc = "Reload config" })

-- save/quit
map({ "n", "i" }, "<C-s>", "<cmd>w<cr>", { desc = "Save" })
map({ "n", "i" }, "<D-s>", "<cmd>w<cr>", { desc = "Save" })
map("n", "<C-q>", "<cmd>q<cr>", { desc = "Quit" })
map("n", "<leader>Q", "<cmd>qa!<cr>", { desc = "Quit all (no save)" })

-- session (<leader>s)
map("n", "<leader>sr", function()
  local name = vim.fn.getcwd():gsub("/", "_")
  local path = vim.fn.stdpath("data") .. "/sessions/" .. name .. ".vim"
  if vim.fn.filereadable(path) == 1 then
    vim.cmd("source " .. vim.fn.fnameescape(path))
  else
    vim.notify("No session for this directory", vim.log.levels.WARN)
  end
end, { desc = "Restore session (cwd)" })

map("n", "<leader>ss", function()
  local cwd = vim.fn.getcwd()
  if cwd == "/" or cwd == vim.env.HOME then
    vim.notify("Skipping session save for " .. cwd, vim.log.levels.WARN)
    return
  end
  local dir = vim.fn.stdpath("data") .. "/sessions"
  vim.fn.mkdir(dir, "p")
  local name = cwd:gsub("/", "_")
  vim.cmd("mksession! " .. vim.fn.fnameescape(dir .. "/" .. name .. ".vim"))
  vim.notify("Session saved")
end, { desc = "Save session (cwd)" })
