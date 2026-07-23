local vault_path = vim.fn.expand("~/vaults/carbon")
if not vim.uv.fs_stat(vault_path) then
  return
end

require("obsidian").setup({
  workspaces = {
    {
      name = "carbon",
      path = "~/vaults/carbon",
    },
  },

  -- notes created in vault root
  new_notes_location = "current_dir",

  daily_notes = {
    folder = "Daily",
    date_format = "%Y-%m-%d",
  },

  templates = {
    folder = "Templates",
    date_format = "%Y-%m-%d",
    time_format = "%H:%M",
  },

  -- completion via blink.compat bridge
  completion = {
    nvim_cmp = true,
    min_chars = 2,
  },

  disable_frontmatter = true,

  picker = {
    name = "telescope.nvim",
    note_mappings = {
      new = "<C-x>",
      insert_link = "<C-l>",
    },
  },

  -- use title as filename, preserving spaces
  note_id_func = function(title)
    if title then
      return title
    end
    return tostring(os.time())
  end,

  follow_url_func = function(url)
    vim.fn.jobstart({ "open", url })
  end,

  follow_img_func = function(img)
    vim.fn.jobstart({ "qlmanage", "-p", img })
  end,

  attachments = {
    img_folder = "assets/imgs",
  },

  -- mappings applied in obsidian vault buffers only
  mappings = {
    ["gf"] = {
      action = function()
        return require("obsidian").util.gf_passthrough()
      end,
      opts = { noremap = false, expr = true, buffer = true },
    },
    ["<cr>"] = {
      action = function()
        return require("obsidian").util.smart_action()
      end,
      opts = { buffer = true, expr = true },
    },
  },
})

-- Obsidian keymaps (<leader>o)
local map = vim.keymap.set
map("n", "<leader>oo", "<cmd>ObsidianOpen<cr>", { desc = "Open in Obsidian app" })
map("n", "<leader>on", "<cmd>ObsidianNew<cr>", { desc = "New note" })
map("n", "<leader>oN", "<cmd>ObsidianNewFromTemplate<cr>", { desc = "New note from template" })
map("n", "<leader>os", "<cmd>ObsidianQuickSwitch<cr>", { desc = "Quick switch" })
map("n", "<leader>of", "<cmd>ObsidianSearch<cr>", { desc = "Search vault" })
map("n", "<leader>ob", "<cmd>ObsidianBacklinks<cr>", { desc = "Backlinks" })
map("n", "<leader>ot", "<cmd>ObsidianToday<cr>", { desc = "Today's daily note" })
map("n", "<leader>oy", "<cmd>ObsidianYesterday<cr>", { desc = "Yesterday's daily note" })
map("n", "<leader>om", "<cmd>ObsidianTomorrow<cr>", { desc = "Tomorrow's daily note" })
map("n", "<leader>oi", "<cmd>ObsidianTemplate<cr>", { desc = "Insert template" })
map("n", "<leader>ol", "<cmd>ObsidianLinks<cr>", { desc = "Links in buffer" })
map("n", "<leader>og", "<cmd>ObsidianTags<cr>", { desc = "Tags" })
map("n", "<leader>oc", "<cmd>ObsidianToggleCheckbox<cr>", { desc = "Toggle checkbox" })
map("n", "<leader>or", "<cmd>ObsidianRename<cr>", { desc = "Rename note" })
map("n", "<leader>op", "<cmd>ObsidianPasteImg<cr>", { desc = "Paste image" })
map("v", "<leader>ol", "<cmd>ObsidianLink<cr>", { desc = "Link selection" })
map("v", "<leader>on", "<cmd>ObsidianLinkNew<cr>", { desc = "Link selection to new note" })
map("v", "<leader>oe", "<cmd>ObsidianExtractNote<cr>", { desc = "Extract to new note" })
