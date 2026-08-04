require("blink.cmp").setup({
  keymap = { preset = "enter" },
  sources = {
    default = { "lsp", "path", "buffer" },
    per_filetype = {
      markdown = { "lsp", "obsidian", "path", "buffer" },
    },
    providers = {
      obsidian = {
        name = "obsidian",
        module = "blink.compat.source",
        async = true,
      },
    },
  },
})
