require("oil").setup({
  default_file_explorer = true,
  view_options = {
    show_hidden = true,
  },
  keymaps = {
    ["<C-h>"] = false, -- don't override window nav
    ["<C-l>"] = false,
  },
})

vim.keymap.set("n", "<leader>e", "<cmd>Oil<cr>", { desc = "File explorer (Oil)" })
vim.keymap.set("n", "-", "<cmd>Oil<cr>", { desc = "File explorer (Oil)" })
