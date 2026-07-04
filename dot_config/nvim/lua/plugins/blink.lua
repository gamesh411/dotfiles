require("blink.cmp").setup({
  keymap = { preset = "super-tab" },
  sources = {
    default = { "lsp", "supermaven", "path", "buffer" },
    per_filetype = {
      markdown = { "lsp", "obsidian", "supermaven", "path", "buffer" },
    },
    providers = {
      supermaven = {
        name = "supermaven",
        module = "blink-cmp-supermaven",
        async = true,
      },
      obsidian = {
        name = "obsidian",
        module = "blink.compat.source",
        async = true,
      },
    },
  },
})
