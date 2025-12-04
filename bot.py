import discord
from discord import app_commands
from discord.ext import tasks
import json
import os
import re
import csv
import asyncio
import hashlib
import io
import aiohttp
from datetime import datetime, timezone
from typing import Optional, List
from dotenv import load_dotenv
from db import BotDatabase
from PIL import Image
import pytesseract
import imagehash


# --- Button & Modal untuk Ticket System ---
class UsernameModal(discord.ui.Modal, title="🎫 Create New Ticket"):
    """Modal untuk input username game"""
    username_input = discord.ui.TextInput(
        label="Username Game Anda",
        placeholder="Contoh: AbuyyXZ777",
        min_length=3,
        max_length=50,
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        username = self.username_input.value.strip()
        
        # Validasi username
        if len(username) < 3:
            await interaction.followup.send(
                "❌ Username game minimal 3 karakter!",
                ephemeral=True
            )
            return
        
        # Cek apakah user sudah punya ticket aktif
        existing_ticket = db.get_open_ticket(interaction.guild.id, interaction.user.id)
        if existing_ticket:
            # Validasi apakah channel masih exist
            channel = interaction.guild.get_channel(int(existing_ticket['channel_id']))
            
            if channel:
                # Channel masih ada, user tidak bisa buat ticket baru
                await interaction.followup.send(
                    f"❌ Anda sudah punya ticket aktif: {channel.mention}\n"
                    f"Gunakan `/close` untuk tutup ticket lama sebelum buat ticket baru.",
                    ephemeral=True
                )
                return
            else:
                # Channel sudah tidak ada (mungkin dihapus manual), auto-close ticket
                db.close_ticket(existing_ticket['id'], interaction.user.id)
                print(f"⚠️ Auto-closed orphaned ticket #{existing_ticket['ticket_number']} (channel deleted)")
        
        # Cari atau buat kategori TICKETS
        category = discord.utils.get(interaction.guild.categories, name="TICKETS")
        if not category:
            try:
                category = await interaction.guild.create_category(name="TICKETS")
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Bot tidak punya permission untuk membuat kategori.\n"
                    "Enable `Manage Channels` permission untuk bot role.",
                    ephemeral=True
                )
                return
        
        # Buat ticket channel
        try:
            # Permission: only ticket creator and admins can see
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True
                )
            }
            
            # Add admin role permissions if configured
            guild_config = db.get_guild_config(interaction.guild.id)
            admin_roles = guild_config.get('admin_roles', [])
            for role_id in admin_roles:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True
                    )
            
            # Create channel first (tanpa ticket number di nama)
            channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                category=category,
                overwrites=overwrites,
                topic=f"Ticket - {interaction.user.name} - Game: {username}"
            )
            
            # Save to database (ticket_number auto-generated)
            ticket_id = db.create_ticket(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                channel_id=channel.id,
                game_username=username
            )
            
            if not ticket_id:
                await channel.delete()
                await interaction.followup.send(
                    "❌ Gagal membuat ticket di database. Coba lagi.",
                    ephemeral=True
                )
                return
            
            # Get ticket info untuk ambil ticket_number
            ticket_info = db.get_ticket_by_channel(channel.id)
            ticket_number = ticket_info['ticket_number'] if ticket_info else 0
            
            # Rename channel dengan ticket number (4 digit format)
            await channel.edit(
                name=f"ticket-{ticket_number:04d}-{interaction.user.name}",
                topic=f"Ticket #{ticket_number:04d} - {interaction.user.name} - Game: {username}"
            )
            
            # Welcome message dengan WARNING
            welcome_embed = discord.Embed(
                title=f"🎫 Ticket #{ticket_number:04d}",
                description=f"Selamat datang, {interaction.user.mention}!",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            welcome_embed.add_field(
                name="📝 Game Username",
                value=f"`{username}`",
                inline=False
            )
            
            # Get Admin & Owner roles
            guild_config = db.get_guild_config(interaction.guild.id)
            admin_roles = guild_config.get('admin_roles', [])
            owner = interaction.guild.owner
            
            admin_mentions = []
            for role_id in admin_roles:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    admin_mentions.append(role.mention)
            
            # Mention admin & owner
            mention_text = f"{owner.mention} "
            if admin_mentions:
                mention_text += " ".join(admin_mentions)
            
            welcome_embed.add_field(
                name="👉 Admin/Owner",
                value=f"{mention_text}\n*Admin akan dinotifikasi saat bukti transfer dikirim*",
                inline=False
            )
            
            # Get all items from database
            items = db.get_all_items(interaction.guild.id)
            if not items:
                db.init_default_items(interaction.guild.id)
                items = db.get_all_items(interaction.guild.id)
            
            rate = db.get_robux_rate(interaction.guild.id)
            
            # Build item list
            items_text = []
            for item in items:
                items_text.append(f"**{item['name']}:** {item['robux']} R$ • Rp{item['price_idr']:,}")
            
            welcome_embed.add_field(
                name=f"💎 Item & Harga (Rate: Rp{rate}/Robux)",
                value="\n".join(items_text),
                inline=False
            )
            
            welcome_embed.set_footer(text=f"Ticket #{ticket_number:04d} • 4-Layer Fraud Detection Active")
            
            await channel.send(f"{mention_text}", embed=welcome_embed)
            
            # Create Select Menu untuk pilih item langsung
            from discord import SelectOption
            
            class ItemSelectView(discord.ui.View):
                def __init__(self, guild_id: int, ticket_id: int):
                    super().__init__(timeout=None)  # Persistent
                    self.guild_id = guild_id
                    self.ticket_id = ticket_id
                
                @discord.ui.select(
                    placeholder="🛒 Pilih item yang ingin dibeli...",
                    min_values=1,
                    max_values=1,
                    custom_id="item_select_persistent"
                )
                async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
                    selected_item_code = select.values[0]
                    
                    # Get item data
                    item_data = db.get_item_price(self.guild_id, selected_item_code)
                    
                    if not item_data:
                        await interaction.response.send_message("❌ Item tidak ditemukan.", ephemeral=True)
                        return
                    
                    # Use module-level QuantityModal class (no longer nested)
                    await interaction.response.send_modal(QuantityModal(item_data, self.ticket_id))
            
            # Build dynamic options dari database
            items = db.get_all_items(interaction.guild.id)
            options = []
            for item in items[:25]:  # Discord max 25 options
                options.append(
                    SelectOption(
                        label=item['name'],
                        value=item['code'],
                        description=f"{item['robux']} R$ • Rp{item['price_idr']:,}",
                        emoji="🎮"
                    )
                )
            
            # Set options ke select menu
            view = ItemSelectView(interaction.guild.id, ticket_id)
            view.children[0].options = options
            
            add_prompt_embed = discord.Embed(
                title="🛍️ Pilih Item",
                description=(
                    f"{interaction.user.mention}\n\n"
                    "⬇️ **Pilih item dari menu di bawah ini:**\n\n"
                    "🔹 Klik dropdown menu\n"
                    "🔹 Pilih item yang diinginkan\n"
                    "🔹 Masukkan jumlah (quantity)\n"
                    "🔹 Ulangi untuk item lain jika perlu"
                ),
                color=discord.Color.blue()
            )
            
            await channel.send(embed=add_prompt_embed, view=view)
            
            # Notify user (redirect mereka ke channel)
            notify_message = await interaction.followup.send(
                f"✅ Ticket berhasil dibuat!\n\n"
                f"🎫 **Ticket:** {channel.mention}\n"
                f"📝 **Username:** `{username}`\n\n"
                f"Silakan buka channel ticket Anda dan gunakan `/add` untuk order!",
                ephemeral=True
            )
            
            # Auto-delete notification setelah 15 detik (background task)
            import asyncio
            asyncio.create_task(delete_message_after_delay(notify_message, 15))
            
            # Log action
            db.log_action(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                action="create_ticket_button",
                details=f"Ticket #{ticket_number} - Channel: {channel.id} - Game: {username}"
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Bot tidak punya permission untuk membuat channel.\n"
                "Enable `Manage Channels` permission untuk bot role.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error membuat ticket: {e}",
                ephemeral=True
            )


async def delete_message_after_delay(message, delay_seconds):
    """Helper function untuk delete message setelah delay"""
    try:
        import asyncio
        await asyncio.sleep(delay_seconds)
        await message.delete()
    except:
        pass  # Ignore jika message sudah dihapus


class QuantityModal(discord.ui.Modal):
    """Modal untuk input jumlah item - didefinisikan di module level"""
    def __init__(self, item_data: dict, ticket_id: int):
        super().__init__(title=f"📊 Jumlah: {item_data['name']}")
        self.item_data = item_data
        self.ticket_id = ticket_id
        
        # Create TextInput instance
        self.quantity_input = discord.ui.TextInput(
            label="Quantity",
            placeholder="Masukkan jumlah (1-5)",
            min_length=1,
            max_length=1,
            required=True,
            style=discord.TextStyle.short
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, modal_interaction: discord.Interaction):
        """Handle quantity modal submit"""
        await modal_interaction.response.defer(ephemeral=True)
        
        try:
            qty = int(self.quantity_input.value)
            
            if qty < 1 or qty > 5:
                await modal_interaction.followup.send(
                    "❌ Quantity harus antara 1-5!",
                    ephemeral=True
                )
                return
            
            # Calculate total
            price = self.item_data['price_idr']
            total = price * qty
            
            # Add item to ticket (database schema: ticket_id, item_name, amount)
            db.add_item_to_ticket(
                ticket_id=self.ticket_id,
                item_name=self.item_data['name'],
                amount=total
            )
            
            # Get updated ticket items
            ticket_items = db.get_ticket_items(self.ticket_id)
            grand_total = sum(item['amount'] for item in ticket_items)
            
            # Build item list
            items_text = []
            for item in ticket_items:
                items_text.append(
                    f"• **{item['item_name']}** = Rp{item['amount']:,}"
                )
            
            embed = discord.Embed(
                title="✅ Item berhasil ditambahkan!",
                description=f"**{self.item_data['name']}** x{qty} = Rp{total:,}",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📋 Keranjang Belanja",
                value="\n".join(items_text),
                inline=False
            )
            
            embed.add_field(
                name="💰 Grand Total",
                value=f"**Rp{grand_total:,}**",
                inline=False
            )
            
            embed.add_field(
                name="📸 Langkah Selanjutnya",
                value="Silakan **scan QRIS** yang sudah dikirim sebelumnya, lalu kirim **bukti transfer** di sini!",
                inline=False
            )
            
            await modal_interaction.followup.send(embed=embed, ephemeral=True)
            
        except ValueError:
            await modal_interaction.followup.send(
                "❌ Input tidak valid. Masukkan angka 1-5.",
                ephemeral=True
            )
        except Exception as e:
            print(f"❌ Error in QuantityModal.on_submit: {e}")
            import traceback
            traceback.print_exc()
            await modal_interaction.followup.send(
                f"❌ Terjadi error: {e}",
                ephemeral=True
            )


class CreateTicketButton(discord.ui.View):
    """Persistent button untuk create ticket"""
    def __init__(self):
        super().__init__(timeout=None)  # Button persistent (no timeout)
    
    @discord.ui.button(
        label="Create Ticket",
        style=discord.ButtonStyle.primary,
        emoji="🎫",
        custom_id="create_ticket_button"
    )
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle button click to open modal"""
        modal = UsernameModal()
        await interaction.response.send_modal(modal)


# --- Middleman Ticket System ---

class MiddlemanModal(discord.ui.Modal, title="🤝 Create Middleman Ticket"):
    """Modal untuk input middleman transaction details"""
    def __init__(self, fee_payer: str = 'buyer'):
        super().__init__()
        self.fee_payer = fee_payer  # 'buyer', 'seller', or 'split'
    
    buyer_username = discord.ui.TextInput(
        label="Username Buyer (in-game)",
        placeholder="Contoh: BuyerXYZ123",
        min_length=3,
        max_length=50,
        required=True,
        style=discord.TextStyle.short
    )
    
    seller_username = discord.ui.TextInput(
        label="Username/ID Seller",
        placeholder="Contoh: @seller atau SellerABC456",
        min_length=3,
        max_length=100,
        required=True,
        style=discord.TextStyle.short
    )
    
    item_description = discord.ui.TextInput(
        label="Item/Jasa",
        placeholder="Contoh: Akun Level 80 + 1000 Diamonds",
        min_length=5,
        max_length=200,
        required=True,
        style=discord.TextStyle.paragraph
    )
    
    deal_price = discord.ui.TextInput(
        label="Harga Deal (Rupiah, angka saja)",
        placeholder="Contoh: 250000",
        min_length=3,
        max_length=10,
        required=True,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        buyer_username = self.buyer_username.value.strip()
        seller_username = self.seller_username.value.strip()
        item_desc = self.item_description.value.strip()
        
        # Validasi harga
        try:
            deal_price = int(self.deal_price.value.strip().replace(".", "").replace(",", ""))
            if deal_price < 1000:
                await interaction.followup.send("❌ Harga minimal Rp1.000!", ephemeral=True)
                return
            if deal_price > 100000000:
                await interaction.followup.send("❌ Harga maksimal Rp100.000.000!", ephemeral=True)
                return
        except ValueError:
            await interaction.followup.send("❌ Harga harus berupa angka yang valid!", ephemeral=True)
            return
        
        # Calculate middleman fee
        mm_fee = calculate_mm_fee(deal_price)
        
        # Validate split fee (only for >5M)
        if self.fee_payer == 'split' and deal_price < 5000000:
            await interaction.followup.send(
                "❌ **Split Fee hanya tersedia untuk transaksi di atas Rp5.000.000!**\n"
                f"Harga deal Anda: Rp{deal_price:,}\n\n"
                "Silakan pilih opsi **Buyer Pays** atau **Seller Pays**.",
                ephemeral=True
            )
            return
        
        # Calculate payments based on fee_payer
        if self.fee_payer == 'buyer':
            total_payment = deal_price + mm_fee  # Buyer pays deal + full fee
            seller_receives = deal_price  # Seller gets full deal price
            fee_info = f"**Fee dibayar:** Buyer (Rp{mm_fee:,})"
        elif self.fee_payer == 'seller':
            total_payment = deal_price  # Buyer only pays deal price
            seller_receives = deal_price - mm_fee  # Seller gets deal - fee
            fee_info = f"**Fee dibayar:** Seller (Rp{mm_fee:,})"
        else:  # split (50:50)
            split_fee = mm_fee // 2
            remaining_fee = mm_fee - split_fee  # Handle odd numbers
            total_payment = deal_price + split_fee  # Buyer pays deal + half fee
            seller_receives = deal_price - remaining_fee  # Seller gets deal - half fee
            fee_info = f"**Fee split 50:50:** Buyer Rp{split_fee:,} + Seller Rp{remaining_fee:,}"
        
        # Cek apakah user sudah punya ticket aktif
        existing_ticket = db.get_open_ticket(interaction.guild.id, interaction.user.id)
        if existing_ticket:
            channel = interaction.guild.get_channel(int(existing_ticket['channel_id']))
            if channel:
                await interaction.followup.send(
                    f"❌ Anda sudah punya ticket aktif: {channel.mention}\n"
                    f"Gunakan `/close` untuk tutup ticket lama sebelum buat ticket baru.",
                    ephemeral=True
                )
                return
            else:
                db.close_ticket(existing_ticket['id'], interaction.user.id)
        
        # Cari atau buat kategori TICKET MIDDLEMAN
        category = discord.utils.get(interaction.guild.categories, name="TICKET MIDDLEMAN")
        if not category:
            try:
                category = await interaction.guild.create_category(name="TICKET MIDDLEMAN")
            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ Bot tidak punya permission untuk membuat kategori.\n"
                    "Enable `Manage Channels` permission untuk bot role.",
                    ephemeral=True
                )
                return
        
        # Buat ticket channel
        try:
            # Permission: buyer, seller (jika mention), dan admins
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    attach_files=True
                ),
                interaction.guild.me: discord.PermissionOverwrite(
                    read_messages=True,
                    send_messages=True,
                    manage_channels=True,
                    manage_messages=True
                )
            }
            
            # Add admin role permissions
            guild_config = db.get_guild_config(interaction.guild.id)
            admin_roles = guild_config.get('admin_roles', [])
            for role_id in admin_roles:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        manage_messages=True
                    )
            
            # Extract seller ID jika mention
            seller_id = None
            if seller_username.startswith('<@') and seller_username.endswith('>'):
                seller_id = seller_username.strip('<@!>').strip('<@>')
                try:
                    seller_member = await interaction.guild.fetch_member(int(seller_id))
                    overwrites[seller_member] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        attach_files=True
                    )
                except:
                    pass
            
            # Create channel
            channel = await interaction.guild.create_text_channel(
                name=f"mm-{interaction.user.name}",
                category=category,
                overwrites=overwrites,
                topic=f"Middleman Ticket - Buyer: {interaction.user.name} - Seller: {seller_username}"
            )
            
            # Save to database
            ticket_id = db.create_ticket(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                channel_id=channel.id,
                game_username=buyer_username,
                ticket_type='middleman',
                seller_id=seller_id,
                seller_username=seller_username,
                item_description=item_desc,
                deal_price=deal_price,
                mm_fee=mm_fee,
                fee_payer=self.fee_payer
            )
            
            if not ticket_id:
                await channel.delete()
                await interaction.followup.send(
                    "❌ Gagal membuat ticket di database. Coba lagi.",
                    ephemeral=True
                )
                return
            
            # Get ticket info
            ticket_info = db.get_ticket_by_channel(channel.id)
            ticket_number = ticket_info['ticket_number'] if ticket_info else 0
            
            # Rename channel dengan ticket number
            await channel.edit(
                name=f"mm-{ticket_number:04d}-{interaction.user.name}",
                topic=f"Middleman Ticket #{ticket_number:04d} - {interaction.user.name} ↔ {seller_username}"
            )
            
            # Welcome embed untuk middleman
            welcome_embed = discord.Embed(
                title=f"🤝 Middleman Ticket #{ticket_number:04d}",
                description=f"Selamat datang di layanan Middleman!\n\nTicket ini akan memfasilitasi transaksi antara buyer dan seller dengan aman.",
                color=0xFF9900,  # Orange untuk middleman
                timestamp=datetime.now()
            )
            
            welcome_embed.add_field(
                name="👤 Buyer",
                value=f"{interaction.user.mention}\nUsername: `{buyer_username}`",
                inline=True
            )
            
            welcome_embed.add_field(
                name="👤 Seller",
                value=f"`{seller_username}`",
                inline=True
            )
            
            welcome_embed.add_field(
                name="\u200b",
                value="\u200b",
                inline=True
            )
            
            welcome_embed.add_field(
                name="📦 Item/Jasa",
                value=f"`{item_desc}`",
                inline=False
            )
            
            welcome_embed.add_field(
                name="💰 Detail Pembayaran",
                value=(
                    f"**Harga Deal:** Rp{deal_price:,}\n"
                    f"**Fee Middleman:** Rp{mm_fee:,}\n"
                    f"{fee_info}\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"**Buyer Transfer:** **Rp{total_payment:,}**\n"
                    f"**Seller Terima:** **Rp{seller_receives:,}**"
                ),
                inline=False
            )
            
            # Get admin mentions
            owner = interaction.guild.owner
            admin_mentions = []
            for role_id in admin_roles:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    admin_mentions.append(role.mention)
            
            mention_text = f"{owner.mention} "
            if admin_mentions:
                mention_text += " ".join(admin_mentions)
            
            welcome_embed.add_field(
                name="👥 Admin/Middleman",
                value=f"{mention_text}\n*Admin akan memfasilitasi transaksi ini*",
                inline=False
            )
            
            welcome_embed.add_field(
                name="📋 Alur Transaksi",
                value=(
                    "**Step 1:** Buyer transfer **Rp{:,}** ke rekening middleman\n"
                    "**Step 2:** Upload bukti transfer (screenshot ASLI)\n"
                    "**Step 3:** Admin verifikasi pembayaran buyer\n"
                    "**Step 4:** Seller kirim item/jasa ke buyer\n"
                    "**Step 5:** Seller upload bukti pengiriman\n"
                    "**Step 6:** Admin approve & release dana ke seller\n\n"
                    "**Note:** Gunakan `/close` jika ada pembatalan"
                ).format(total_payment),
                inline=False
            )
            
            welcome_embed.add_field(
                name="💳 Pembayaran",
                value=(
                    f"**Total Transfer:** Rp{total_payment:,}\n\n"
                    "Admin akan memberikan QRIS untuk pembayaran."
                ),
                inline=False
            )
            
            # WARNING
            welcome_embed.add_field(
                name="⚠️ PENTING: Bukti Transfer",
                value=(
                    "🚨 **Buyer & Seller WAJIB upload bukti ASLI!**\n\n"
                    "❌ **DILARANG:**\n"
                    "• Crop/edit screenshot\n"
                    "• Blur/mosaic data\n"
                    "• Gunakan gambar palsu\n\n"
                    "✅ **WAJIB:**\n"
                    "• Screenshot FULL & ASLI\n"
                    "• Terlihat jelas semua detail\n\n"
                    "⚡ **4-Layer Fraud Detection Active!**\n"
                    "Screenshot palsu akan langsung ditolak."
                ),
                inline=False
            )
            
            welcome_embed.set_footer(text=f"Middleman Ticket #{ticket_number:04d} • Status: Waiting Buyer Payment")
            
            await channel.send(embed=welcome_embed)
            
            # Notify user dengan info fee yang benar
            if self.fee_payer == 'buyer':
                fee_note = f"Fee ditanggung Buyer (Rp{mm_fee:,})"
            elif self.fee_payer == 'seller':
                fee_note = f"Fee ditanggung Seller (Rp{mm_fee:,})"
            else:
                split_fee = mm_fee // 2
                remaining_fee = mm_fee - split_fee
                fee_note = f"Fee split 50:50 (Buyer: Rp{split_fee:,}, Seller: Rp{remaining_fee:,})"
            
            await interaction.followup.send(
                f"✅ Middleman ticket berhasil dibuat!\n\n"
                f"🤝 **Ticket:** {channel.mention}\n"
                f"💰 **Buyer Transfer:** Rp{total_payment:,}\n"
                f"💰 **Seller Terima:** Rp{seller_receives:,}\n"
                f"📊 **{fee_note}**\n\n"
                f"Silakan buka channel ticket dan transfer ke rekening middleman!",
                ephemeral=True
            )
            
            # Log action
            db.log_action(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                action="create_mm_ticket",
                details=f"Ticket #{ticket_number} - MM - Buyer: {buyer_username} - Seller: {seller_username} - Price: Rp{deal_price:,}"
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Bot tidak punya permission untuk membuat channel.\n"
                "Enable `Manage Channels` permission untuk bot role.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error membuat ticket: {e}",
                ephemeral=True
            )


class FeePayerSelectView(discord.ui.View):
    """View dengan dropdown untuk pilih siapa yang bayar fee"""
    def __init__(self):
        super().__init__(timeout=180)  # 3 menit timeout
    
    @discord.ui.select(
        placeholder="📊 Pilih siapa yang bayar fee middleman...",
        options=[
            discord.SelectOption(
                label="Buyer Pays Full Fee",
                value="buyer",
                description="Buyer bayar harga + fee penuh",
                emoji="🔵"
            ),
            discord.SelectOption(
                label="Seller Pays Full Fee",
                value="seller",
                description="Seller terima harga - fee penuh",
                emoji="🟢"
            ),
            discord.SelectOption(
                label="Split Fee 50:50 (Hanya >5 Juta)",
                value="split",
                description="Fee dibagi 50:50 antara buyer & seller",
                emoji="🟡"
            )
        ]
    )
    async def select_fee_payer(self, interaction: discord.Interaction, select: discord.ui.Select):
        fee_payer = select.values[0]
        
        # Show modal dengan fee_payer yang dipilih
        modal = MiddlemanModal(fee_payer=fee_payer)
        await interaction.response.send_modal(modal)


class CreateMiddlemanButton(discord.ui.View):
    """Persistent button untuk create middleman ticket"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(
        label="Create Middleman Ticket",
        style=discord.ButtonStyle.success,
        emoji="🤝",
        custom_id="create_mm_ticket_button"
    )
    async def create_mm_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle button click to show fee payer selection"""
        # Show fee payer select menu
        view = FeePayerSelectView()
        
        embed = discord.Embed(
            title="🤝 Middleman Ticket - Fee Payment",
            description=(
                "Selamat datang di layanan Middleman!\n\n"
                "Silakan pilih **siapa yang akan membayar fee middleman**:\n\n"
                "🔵 **Buyer Pays** - Buyer bayar harga deal + fee penuh\n"
                "🟢 **Seller Pays** - Seller terima harga deal - fee\n"
                "🟡 **Split 50:50** - Fee dibagi rata (hanya untuk >Rp5.000.000)\n\n"
                "**Fee Structure:**\n"
                "• <50K: Gratis\n"
                "• 50K-500K: Rp2.000\n"
                "• 500K-1Juta: Rp5.000\n"
                "• 1Juta-5Juta: Rp7.000\n"
                "• 5Juta-10Juta: Rp10.000\n"
                "• 10Juta+: Rp15.000"
            ),
            color=0xFF9900
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


def calculate_mm_fee(deal_price: int) -> int:
    """Calculate middleman fee based on deal price
    
    Fee structure:
    - <50K: Gratis (Rp0)
    - 50K-500K: Rp2.000
    - 500K-1Juta: Rp5.000
    - 1Juta-5Juta: Rp7.000 (UPDATED)
    - 5Juta-10Juta: Rp10.000
    - 10Juta+: Rp15.000
    """
    if deal_price < 50000:
        return 0
    elif deal_price < 500000:
        return 2000
    elif deal_price < 1000000:
        return 5000
    elif deal_price < 5000000:
        return 7000  # UPDATED: dari 7500 → 7000
    elif deal_price < 10000000:
        return 10000
    else:
        return 15000


# --- MUAT VARIABEL LINGKUNGAN ---
load_dotenv()  # Memuat variabel lingkungan dari file .env

# --- Konfigurasi Awal ---

# Ambil Token Bot
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

SERVER_ID_STR = os.getenv("GUILD_ID")
SERVER_ID = int(SERVER_ID_STR) if SERVER_ID_STR else None 

# Tentukan lokasi penyimpanan data
DATA_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

DB_FILE = os.path.join(DATA_DIR, 'bot_database.db')

# Inisialisasi database
db = BotDatabase(DB_FILE)

# Cooldown tracking untuk channel #cmd-bot (2 menit per user)
cmd_bot_cooldowns = {}  # Format: {(guild_id, user_id): last_command_time}
CMD_BOT_COOLDOWN = 120  # 2 menit dalam detik


# --- Fungsi Bantuan ---
def format_idr(value):
    """Memformat angka menjadi format mata uang IDR."""
    return "Rp{:,.0f}".format(value).replace(',', '.')


def check_cmd_bot_cooldown(interaction: discord.Interaction) -> tuple[bool, int]:
    """
    Check cooldown untuk channel #cmd-bot
    Returns: (is_on_cooldown, remaining_seconds)
    """
    # Hanya apply cooldown jika di channel #cmd-bot
    if interaction.channel.name != "cmd-bot":
        return False, 0
    
    # Admin dan Owner bypass cooldown
    if is_admin_or_owner(interaction):
        return False, 0
    
    # Check cooldown
    key = (interaction.guild.id, interaction.user.id)
    now = datetime.now().timestamp()
    
    if key in cmd_bot_cooldowns:
        elapsed = now - cmd_bot_cooldowns[key]
        if elapsed < CMD_BOT_COOLDOWN:
            remaining = int(CMD_BOT_COOLDOWN - elapsed)
            return True, remaining
    
    # Update last command time
    cmd_bot_cooldowns[key] = now
    return False, 0


# Decorator untuk admin-only commands
def admin_only():
    """Decorator untuk membatasi command ke admin saja"""
    async def predicate(interaction: discord.Interaction) -> bool:
        try:
            # Cek guild config untuk admin roles
            guild_config = db.get_guild_config(interaction.guild.id)
            admin_roles = guild_config.get('admin_roles', [])
            
            # Jika admin roles dikonfigurasi, cek apakah user punya role tersebut
            if admin_roles:
                user_role_ids = [str(role.id) for role in interaction.user.roles]
                if any(role_id in admin_roles for role_id in user_role_ids):
                    return True
            
            # Fallback ke administrator permission
            return interaction.user.guild_permissions.administrator
        except Exception:
            return False
    
    return app_commands.check(predicate)


def is_owner(interaction: discord.Interaction) -> bool:
    """Check apakah user adalah owner server"""
    return interaction.user.id == interaction.guild.owner_id


def is_admin_or_owner(interaction: discord.Interaction) -> bool:
    """Check apakah user adalah admin atau owner"""
    if is_owner(interaction):
        return True
    
    try:
        guild_config = db.get_guild_config(interaction.guild.id)
        admin_roles = guild_config.get('admin_roles', [])
        
        if admin_roles:
            user_role_ids = [str(role.id) for role in interaction.user.roles]
            if any(role_id in admin_roles for role_id in user_role_ids):
                return True
        
        return interaction.user.guild_permissions.administrator
    except Exception:
        return interaction.user.guild_permissions.administrator


def owner_only():
    """Decorator untuk commands yang HANYA untuk Owner"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not is_owner(interaction):
            await interaction.response.send_message(
                "❌ **OWNER ONLY**\n\nCommand ini hanya bisa digunakan oleh Owner server!",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)


async def detect_legitimate_transfer_screenshot(image_url: str) -> dict:
    """HYBRID APPROACH: Detect legitimate transfer screenshots using multiple methods
    
    Methods:
    1. OCR Text Detection (keywords: BERHASIL, SUCCESS, TRANSFER, bank names)
    2. Banking UI Colors (brand detection)
    3. Device Resolution (iPhone/Android/PC)
    4. Receipt Format (high text density, structured layout)
    5. Watermark Patterns (banking app security features)
    
    Returns: dict with is_legitimate (bool), source (str), confidence (float)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return {'is_legitimate': False, 'source': 'unknown', 'confidence': 0}
                
                image_data = await resp.read()
                image = Image.open(io.BytesIO(image_data))
                
                print(f"🔍 HYBRID LEGITIMACY CHECK...")
                
                # Convert to RGB
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                import numpy as np
                img_array = np.array(image)
                h, w, c = img_array.shape
                
                legitimate_indicators = []
                confidence_scores = []
                
                # ========================================
                # METHOD 1: OCR TEXT DETECTION (HIGHEST PRIORITY)
                # ========================================
                try:
                    # Try OCR for banking keywords
                    import pytesseract
                    from PIL import ImageEnhance
                    
                    # Enhance image for better OCR
                    enhancer = ImageEnhance.Contrast(image)
                    enhanced = enhancer.enhance(2.0)
                    
                    # Extract text
                    text = pytesseract.image_to_string(enhanced, lang='ind+eng').upper()
                    
                    print(f"📝 OCR Text extracted: {len(text)} chars")
                    
                    # INDONESIAN BANKING KEYWORDS (40 points each!)
                    banking_keywords = {
                        'BERHASIL': 40,
                        'SUKSES': 40,
                        'SUCCESS': 40,
                        'TRANSFER': 30,
                        'M-TRANSFER': 40,
                        'MOBILE BANKING': 35,
                        'INTERNET BANKING': 35,
                        
                        # Bank Names (30 points)
                        'BCA': 30,
                        'MANDIRI': 30,
                        'BRI': 30,
                        'BNI': 30,
                        'CIMB': 25,
                        'PERMATA': 25,
                        'DANAMON': 25,
                        'BTN': 25,
                        'JAGO': 25,
                        
                        # E-Wallet Names (30 points)
                        'GOPAY': 30,
                        'OVO': 30,
                        'DANA': 30,
                        'SHOPEEPAY': 30,
                        'LINKAJA': 30,
                        
                        # Transfer-specific terms
                        'PENERIMA': 20,
                        'PENGIRIM': 20,
                        'NOMINAL': 20,
                        'REKENING': 20,
                        'BIAYA ADMIN': 15,
                        'TOTAL': 15,
                        
                        # Date/Time indicators
                        'TANGGAL': 10,
                        'WAKTU': 10,
                        'JAM': 10,
                    }
                    
                    for keyword, points in banking_keywords.items():
                        if keyword in text:
                            legitimate_indicators.append(f"OCR: '{keyword}' detected")
                            confidence_scores.append(points)
                            print(f"   ✅ Found keyword: {keyword} (+{points} points)")
                    
                    # Detect account numbers (10-16 digits)
                    import re
                    account_numbers = re.findall(r'\b\d{10,16}\b', text)
                    if account_numbers:
                        legitimate_indicators.append(f"OCR: {len(account_numbers)} account number(s)")
                        confidence_scores.append(20)
                        print(f"   ✅ Found {len(account_numbers)} account numbers (+20 points)")
                    
                    # Detect currency (Rp)
                    if 'RP' in text or 'IDR' in text:
                        legitimate_indicators.append("OCR: Indonesian currency")
                        confidence_scores.append(15)
                        print(f"   ✅ Currency detected (+15 points)")
                        
                except Exception as ocr_error:
                    print(f"   ⚠️ OCR unavailable (Tesseract not installed)")
                
                # ========================================
                # METHOD 2: BANKING UI COLOR DETECTION
                # ========================================
                header_region = img_array[:int(h*0.2), :, :]
                avg_r = np.mean(header_region[:,:,0])
                avg_g = np.mean(header_region[:,:,1])
                avg_b = np.mean(header_region[:,:,2])
                
                # Expanded color detection with tolerance
                banking_colors = [
                    # (R_min, R_max, G_min, G_max, B_min, B_max, name, points)
                    (0, 60, 40, 140, 140, 230, "BCA Blue", 25),
                    (190, 255, 170, 240, 0, 120, "Mandiri Yellow", 25),
                    (0, 60, 140, 210, 0, 90, "GoPay Green", 25),
                    (50, 110, 30, 90, 120, 190, "OVO Purple", 25),
                    (10, 90, 110, 190, 210, 255, "Dana Blue", 25),
                    (190, 255, 50, 110, 20, 80, "ShopeePay Orange", 25),
                    (0, 70, 70, 140, 150, 210, "BRI Blue", 25),
                    (200, 255, 90, 140, 0, 70, "BNI Orange", 25),
                ]
                
                for r_min, r_max, g_min, g_max, b_min, b_max, name, points in banking_colors:
                    if r_min <= avg_r <= r_max and g_min <= avg_g <= g_max and b_min <= avg_b <= b_max:
                        legitimate_indicators.append(f"UI Color: {name}")
                        confidence_scores.append(points)
                        print(f"   🎨 Detected {name} (+{points} points)")
                
                # ========================================
                # METHOD 3: DEVICE RESOLUTION (EXPANDED)
                # ========================================
                # Comprehensive device resolution database
                device_resolutions = {
                    # iPhone (width, height_range_min, height_range_max, name, points)
                    1290: (2700, 2900, "iPhone 15 Pro Max", 20),
                    1179: (2500, 2600, "iPhone 15/14 Pro", 20),
                    1170: (2400, 2600, "iPhone 13/12", 20),
                    1284: (2700, 2800, "iPhone 12 Pro Max", 20),
                    1125: (2300, 2500, "iPhone 11 Pro", 20),
                    828: (1700, 1900, "iPhone 11/XR", 20),
                    750: (1300, 1400, "iPhone SE/8", 20),
                    
                    # Android (common widths)
                    1080: (1900, 2500, "Android FHD+", 20),
                    1440: (2800, 3200, "Android QHD+", 20),
                    720: (1400, 1700, "Android HD+", 20),
                    1200: (2400, 2700, "Android Tablet", 15),
                    
                    # PC/Laptop screenshots
                    1920: (1000, 1200, "PC Full HD", 15),
                    1366: (700, 900, "Laptop HD", 15),
                    2560: (1300, 1600, "PC 2K", 15),
                    3840: (2100, 2300, "PC 4K", 15),
                }
                
                for width, (h_min, h_max, device_name, points) in device_resolutions.items():
                    if w == width and h_min <= h <= h_max:
                        legitimate_indicators.append(f"Device: {device_name}")
                        confidence_scores.append(points)
                        print(f"   📱 Detected {device_name} ({w}x{h}) (+{points} points)")
                        break
                
                # ========================================
                # METHOD 4: RECEIPT FORMAT DETECTION
                # ========================================
                gray = np.mean(img_array, axis=2)
                grad_x = np.abs(np.diff(gray, axis=1))
                text_density = np.mean(grad_x)
                
                # Receipt characteristics
                if 5 <= text_density <= 15:
                    legitimate_indicators.append("Receipt format: High text density")
                    confidence_scores.append(20)
                    print(f"   📄 Receipt text density: {text_density:.2f} (+20 points)")
                
                # ========================================
                # METHOD 5: WATERMARK/LOGO DETECTION
                # ========================================
                center_region = img_array[int(h*0.3):int(h*0.7), int(w*0.2):int(w*0.8), :]
                center_std = np.std(center_region)
                
                if 30 <= center_std <= 70:
                    legitimate_indicators.append("Security: Watermark pattern")
                    confidence_scores.append(15)
                    print(f"   🔒 Watermark detected (+15 points)")
                
                # ========================================
                # METHOD 6: STATUS BAR (MOBILE SCREENSHOT)
                # ========================================
                status_bar = img_array[:int(h*0.05), :, :]
                status_std = np.std(status_bar)
                if status_std < 20:
                    legitimate_indicators.append("Mobile UI: Status bar")
                    confidence_scores.append(10)
                    print(f"   📱 Mobile status bar (+10 points)")
                
                # ========================================
                # FINAL SCORE CALCULATION
                # ========================================
                total_confidence = min(sum(confidence_scores), 100)
                
                # Determine legitimacy threshold
                # High threshold (60%) because we have OCR now
                is_legitimate = total_confidence >= 50
                
                source = ", ".join(legitimate_indicators) if legitimate_indicators else "unknown"
                
                if is_legitimate:
                    print(f"✅ LEGITIMATE SCREENSHOT! Confidence: {total_confidence:.1f}%")
                    print(f"   Indicators: {len(legitimate_indicators)}")
                else:
                    print(f"⚠️ Screenshot unclear (confidence: {total_confidence:.1f}%)")
                
                return {
                    'is_legitimate': is_legitimate,
                    'source': source,
                    'confidence': total_confidence,
                    'indicators': legitimate_indicators
                }
                
    except Exception as e:
        print(f"⚠️ Error checking legitimate screenshot: {e}")
        import traceback
        traceback.print_exc()
        return {'is_legitimate': False, 'source': 'unknown', 'confidence': 0}


async def detect_image_manipulation(image_url: str) -> dict:
    """Detect image manipulation: scribbles, blur, mosaic, excessive editing
    
    Returns: dict with manipulation_detected (bool), warnings (list), confidence (float)
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    print(f"⚠️ Failed to download image for manipulation check: HTTP {resp.status}")
                    return {'manipulation_detected': False, 'warnings': [], 'confidence': 0}
                
                image_data = await resp.read()
                image = Image.open(io.BytesIO(image_data))
                
                print(f"📷 Image loaded: {image.size} ({image.mode})")
                
                # Convert to RGB if needed
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Convert to numpy array for analysis
                import numpy as np
                img_array = np.array(image)
                
                warnings = []
                confidence_scores = []
                
                h, w, c = img_array.shape
                total_pixels = h * w
                
                print(f"🔍 Analyzing {w}x{h} image ({total_pixels:,} pixels)...")
                
                # === 1. DETECT SCRIBBLES/DRAWINGS (LARGE VIVID COLOR PATCHES) ===
                # Differentiate between UI elements (small, structured) vs scribbles (large, random)
                
                # Convert RGB to HSV manually
                img_float = img_array.astype(float) / 255.0
                r, g, b = img_float[:,:,0], img_float[:,:,1], img_float[:,:,2]
                
                # Calculate Value (brightness)
                v = np.maximum(np.maximum(r, g), b)
                
                # Calculate Saturation
                min_rgb = np.minimum(np.minimum(r, g), b)
                s = np.where(v > 0, (v - min_rgb) / v, 0)
                
                # Count highly saturated AND bright pixels (scribbles, drawings)
                # INCREASED threshold: Saturation > 0.5 (50%) AND Value > 0.5 (50%)
                # This filters out UI buttons and focuses on VIVID scribbles
                scribble_mask = (s > 0.5) & (v > 0.5)
                scribble_pixels = np.sum(scribble_mask)
                scribble_ratio = scribble_pixels / total_pixels
                
                print(f"   🎨 Scribble detection: {scribble_pixels:,} pixels ({scribble_ratio*100:.2f}%)")
                
                # If >5% of image is VERY vivid color, flag as scribble
                # INCREASED from 1% to 5% to avoid false positives from UI elements
                if scribble_ratio > 0.05:
                    warnings.append(f"🎨 **Terdeteksi coretan/gambar warna** ({scribble_ratio*100:.1f}% area)")
                    confidence_scores.append(min(scribble_ratio * 40, 35))
                
                # === 2. DETECT MOSAIC/BLUR (INTENTIONAL PIXELATION) ===
                # Distinguish between:
                # - Natural low-res screenshot (uniform gradient, acceptable)
                # - Intentional mosaic edit (blocky patches in specific areas)
                
                block_size = 20  # Increased from 16 to 20 for better large-area detection
                uniform_blocks = 0
                total_blocks = 0
                high_variance_blocks = 0
                
                for i in range(0, h - block_size, block_size):
                    for j in range(0, w - block_size, block_size):
                        block = img_array[i:i+block_size, j:j+block_size]
                        
                        # Calculate standard deviation for each channel
                        std_r = np.std(block[:,:,0])
                        std_g = np.std(block[:,:,1])
                        std_b = np.std(block[:,:,2])
                        avg_std = (std_r + std_g + std_b) / 3
                        
                        # Very low variance = uniform/mosaic
                        if avg_std < 5:  # Stricter: 5 instead of 8
                            uniform_blocks += 1
                        # High variance = detailed content
                        elif avg_std > 20:
                            high_variance_blocks += 1
                        
                        total_blocks += 1
                
                mosaic_ratio = uniform_blocks / total_blocks if total_blocks > 0 else 0
                detail_ratio = high_variance_blocks / total_blocks if total_blocks > 0 else 0
                
                print(f"   🟦 Mosaic detection: {uniform_blocks}/{total_blocks} uniform blocks ({mosaic_ratio*100:.2f}%)")
                print(f"   ✨ Detail blocks: {high_variance_blocks}/{total_blocks} ({detail_ratio*100:.2f}%)")
                
                # SMART DETECTION:
                # - If >95% uniform AND <5% detail → Likely intentional mosaic/blur
                # - If 70-95% uniform AND >10% detail → Natural low-res screenshot (OK)
                if mosaic_ratio > 0.95 and detail_ratio < 0.05:
                    warnings.append(f"🟦 **Mosaik/blur terdeteksi** ({mosaic_ratio*100:.1f}% area ter-blur)")
                    confidence_scores.append(min((mosaic_ratio - 0.95) * 200, 40))
                
                # === 3. DETECT OVERALL BLUR (Edge sharpness) ===
                # Convert to grayscale
                gray = np.mean(img_array, axis=2)
                
                # Simple edge detection using gradient
                grad_x = np.abs(np.diff(gray, axis=1))
                grad_y = np.abs(np.diff(gray, axis=0))
                
                # Calculate average gradient (edge strength)
                avg_gradient = (np.mean(grad_x) + np.mean(grad_y)) / 2
                
                print(f"   📐 Edge sharpness: {avg_gradient:.2f}")
                
                # LOWERED threshold: Only flag if VERY blurry (<2.0)
                # Screenshot HP typically 3-6, heavily blurred <2
                if avg_gradient < 2.0:
                    warnings.append(f"🌫️ **Gambar sangat blur** (sharpness: {avg_gradient:.1f})")
                    confidence_scores.append(min((2.0 - avg_gradient) * 10, 20))
                
                # Calculate overall confidence
                total_confidence = min(sum(confidence_scores), 100)
                
                # STRICTER: Only flag if confidence >40% (was 15%)
                manipulation_detected = len(warnings) > 0 and total_confidence > 40
                
                print(f"   ⚠️ Warnings: {len(warnings)}, Confidence: {total_confidence:.1f}%")
                
                if manipulation_detected:
                    print(f"🚨 IMAGE MANIPULATION DETECTED!")
                    for warning in warnings:
                        print(f"   {warning}")
                
                return {
                    'manipulation_detected': manipulation_detected,
                    'warnings': warnings,
                    'confidence': total_confidence,
                    'details': {
                        'scribble_ratio': scribble_ratio,
                        'mosaic_ratio': mosaic_ratio,
                        'detail_ratio': detail_ratio,
                        'avg_gradient': avg_gradient
                    }
                }
                
    except Exception as e:
        print(f"⚠️ Error detecting manipulation: {e}")
        import traceback
        traceback.print_exc()
        return {'manipulation_detected': False, 'warnings': [], 'confidence': 0}


# === Helper Function: Image Hash untuk Duplicate Detection ===
async def get_image_hash(image_url: str) -> dict:
    """Download image and generate MULTIPLE perceptual hashes for robust detection
    
    Uses 3 algorithms:
    - dhash: Gradient-based (good for text/receipts)
    - phash: DCT-based (resistant to color changes/watermarks)
    - average_hash: Brightness-based (fallback for simple images)
    
    Returns: Dict with multiple hashes for cross-validation
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    print(f"⚠️ Failed to download image: HTTP {resp.status}")
                    return None
                
                image_data = await resp.read()
                
                # Open image with PIL
                image = Image.open(io.BytesIO(image_data))
                
                # Generate MULTIPLE perceptual hashes
                dhash_result = str(imagehash.dhash(image, hash_size=16))
                phash_result = str(imagehash.phash(image, hash_size=16))
                ahash_result = str(imagehash.average_hash(image, hash_size=16))
                
                # Combine into single searchable string (for database backward compatibility)
                combined_hash = f"{dhash_result}|{phash_result}|{ahash_result}"
                
                print(f"✅ Generated image hashes:")
                print(f"   • dhash: {dhash_result[:16]}... (gradient-based)")
                print(f"   • phash: {phash_result[:16]}... (DCT frequency)")
                print(f"   • ahash: {ahash_result[:16]}... (brightness)")
                
                return {
                    'combined': combined_hash,
                    'dhash': dhash_result,
                    'phash': phash_result,
                    'ahash': ahash_result
                }
                
    except Exception as e:
        print(f"⚠️ Error hashing image: {e}")
        import traceback
        traceback.print_exc()
        return None


async def check_similar_images(guild_id: int, new_hashes: dict, current_ticket_id: int = None) -> dict:
    """Check if similar image exists using MULTI-ALGORITHM comparison
    
    Compares using 3 different algorithms and considers match if ANY algorithm detects similarity:
    - dhash (threshold 25): Gradient comparison, tolerant to color changes
    - phash (threshold 30): DCT frequency, VERY robust to crop/resize/edit
    - ahash (threshold 15): Average brightness, simple but effective
    
    Args:
        guild_id: Guild ID to check
        new_hashes: Dict with dhash, phash, ahash from get_image_hash()
        current_ticket_id: Current ticket ID to exclude from comparison (ONLY for first upload)
    
    Returns: dict with ticket info if similar found, None otherwise
    """
    try:
        # Get all proof hashes from database
        all_tickets = db.get_all_proof_hashes(guild_id)
        
        print(f"🔍 Multi-algorithm similarity check: {len(all_tickets)} tickets in database")
        
        # Parse new hashes
        new_dhash = imagehash.hex_to_hash(new_hashes['dhash'])
        new_phash = imagehash.hex_to_hash(new_hashes['phash'])
        new_ahash = imagehash.hex_to_hash(new_hashes['ahash'])
        
        for ticket in all_tickets:
            if not ticket['proof_hash']:
                continue
            
            # CRITICAL FIX: Check if this is the SAME ticket
            is_same_ticket = current_ticket_id and ticket.get('ticket_id') == current_ticket_id
            
            # Parse stored hash (BACKWARD COMPATIBILITY: handle both old and new format)
            stored_hash_str = ticket['proof_hash']
            
            # Check if it's new format (contains |)
            if '|' in stored_hash_str:
                # New format: dhash|phash|ahash
                parts = stored_hash_str.split('|')
                stored_dhash = imagehash.hex_to_hash(parts[0])
                stored_phash = imagehash.hex_to_hash(parts[1]) if len(parts) > 1 else None
                stored_ahash = imagehash.hex_to_hash(parts[2]) if len(parts) > 2 else None
            else:
                # Old format (single hash - assume it's dhash)
                stored_dhash = imagehash.hex_to_hash(stored_hash_str)
                stored_phash = None
                stored_ahash = None
            
            # Calculate distances for all available algorithms
            dhash_dist = new_dhash - stored_dhash
            phash_dist = new_phash - stored_phash if stored_phash else 999
            ahash_dist = new_ahash - stored_ahash if stored_ahash else 999
            
            print(f"📊 Ticket #{ticket['ticket_number']:04d}:")
            print(f"   • dhash: {dhash_dist} bits (threshold 25)")
            print(f"   • phash: {phash_dist} bits (threshold 30)")
            print(f"   • ahash: {ahash_dist} bits (threshold 15)")
            
            # MULTI-ALGORITHM DETECTION: Match if ANY algorithm detects similarity
            matched = False
            match_algorithm = None
            best_distance = 999
            
            # Check dhash (gradient) - threshold 25 (very tolerant to edits)
            if dhash_dist <= 25:
                matched = True
                match_algorithm = "dhash (gradient)"
                best_distance = dhash_dist
            
            # Check phash (DCT frequency) - threshold 30 (MOST robust for crop/resize)
            if phash_dist <= 30:
                if not matched or phash_dist < best_distance:
                    matched = True
                    match_algorithm = "phash (frequency)"
                    best_distance = phash_dist
            
            # Check ahash (brightness) - threshold 15 (moderate)
            if ahash_dist <= 15:
                if not matched or ahash_dist < best_distance:
                    matched = True
                    match_algorithm = "ahash (brightness)"
                    best_distance = ahash_dist
            
            if matched:
                similarity_pct = ((256 - best_distance) / 256 * 100)
                
                # CRITICAL CHECK: Is this user trying to upload DUPLICATE to SAME ticket?
                if is_same_ticket:
                    print(f"🚨 SAME TICKET DUPLICATE! User trying to replace proof with SAME image!")
                    print(f"   Similarity: {similarity_pct:.1f}% (distance: {best_distance} bits)")
                    return {
                        'ticket_number': ticket['ticket_number'],
                        'user_id': ticket['user_id'],
                        'game_username': ticket['game_username'],
                        'created_at': ticket['created_at'],
                        'status': ticket['status'],
                        'similarity': f"{similarity_pct:.1f}%",
                        'distance': best_distance,
                        'algorithm': match_algorithm,
                        'all_distances': f"dhash:{dhash_dist}, phash:{phash_dist}, ahash:{ahash_dist}",
                        'is_same_ticket': True
                    }
                
                print(f"🚨 DUPLICATE DETECTED via {match_algorithm}!")
                print(f"   Similarity: {similarity_pct:.1f}% (distance: {best_distance} bits)")
                
                return {
                    'ticket_number': ticket['ticket_number'],
                    'user_id': ticket['user_id'],
                    'game_username': ticket['game_username'],
                    'created_at': ticket['created_at'],
                    'status': ticket['status'],
                    'similarity': f"{similarity_pct:.1f}%",
                    'distance': best_distance,
                    'algorithm': match_algorithm,
                    'all_distances': f"dhash:{dhash_dist}, phash:{phash_dist}, ahash:{ahash_dist}",
                    'is_same_ticket': False
                }
        
        print(f"✅ No similar images found (checked {len(all_tickets)} tickets)")
        return None
        
    except Exception as e:
        print(f"⚠️ Error checking similar images: {e}")
        import traceback
        traceback.print_exc()
        return None


# === Helper Function: OCR Amount Detection ===
async def extract_amount_from_image(image_url: str) -> Optional[int]:
    """Extract transfer amount from screenshot using OCR
    
    Returns: Detected amount as integer, or None if not found
    """
    try:
        # Check if tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            # Tesseract not installed, skip OCR
            return None
        
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return None
                
                image_data = await resp.read()
                
                # Open image with PIL
                image = Image.open(io.BytesIO(image_data))
                
                # Convert to RGB if needed
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # OCR to extract text
                text = pytesseract.image_to_string(image, lang='eng')
                
                # Find amounts in text (IDR format: 251,000.00 or 251000 or 251.000)
                # Pattern: angka dengan separator titik/koma
                patterns = [
                    r'(?:IDR|Rp)?\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',  # IDR 251,000.00
                    r'(?:Total|Tagihan|Bayar)[\s:]+(?:IDR|Rp)?\s*(\d{1,3}(?:[.,]\d{3})*)',  # Total: 251,000
                    r'(\d{3}[.,]\d{3}[.,]\d{2,3})',  # 251.000.00 or 251,000.00
                ]
                
                detected_amounts = []
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        # Clean: remove dots and commas
                        amount_str = re.sub(r'[.,]', '', match)
                        try:
                            amount = int(amount_str)
                            # Filter reasonable amounts (100 - 100M)
                            if 100 <= amount <= 100000000:
                                detected_amounts.append(amount)
                        except ValueError:
                            continue
                
                # Return most common amount or largest
                if detected_amounts:
                    # Return the most likely amount (largest one in reasonable range)
                    return max(detected_amounts)
                
                return None
                
    except Exception as e:
        print(f"⚠️ Error OCR amount detection: {e}")
        return None


async def extract_transfer_signature(image_url: str) -> Optional[str]:
    """Extract transfer signature (account number + date + amount) for duplicate detection
    
    Returns: Signature string like "6241530865_03/12/2025_150000", or None if OCR not available
    """
    try:
        # Check if tesseract is available
        try:
            pytesseract.get_tesseract_version()
        except Exception:
            return None
        
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return None
                
                image_data = await resp.read()
                image = Image.open(io.BytesIO(image_data))
                
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # OCR to extract text
                text = pytesseract.image_to_string(image, lang='eng')
                
                # Extract key information
                account_number = None
                date_str = None
                amount = None
                
                # Find account number (Indonesian bank format: 10-16 digits)
                acc_pattern = r'(?:Ke|ke|To)\s*:?\s*(\d{10,16})'
                acc_match = re.search(acc_pattern, text)
                if acc_match:
                    account_number = acc_match.group(1)
                
                # Find date (DD/MM/YYYY or DD-MM-YYYY)
                date_pattern = r'(\d{2}[/-]\d{2}[/-]\d{4})'
                date_match = re.search(date_pattern, text)
                if date_match:
                    date_str = date_match.group(1).replace('-', '/')
                
                # Find amount
                amount_patterns = [
                    r'Rp\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
                    r'(\d{3}[.,]\d{3}[.,]\d{2,3})'
                ]
                
                for pattern in amount_patterns:
                    amt_match = re.search(pattern, text)
                    if amt_match:
                        amount_str = re.sub(r'[.,]', '', amt_match.group(1))
                        try:
                            amount = int(amount_str)
                            if 100 <= amount <= 100000000:
                                break
                        except:
                            continue
                
                # Create signature if we have at least account and amount
                if account_number and amount:
                    signature = f"{account_number}_{date_str or 'nodate'}_{amount}"
                    print(f"✅ Transfer signature: {signature}")
                    return signature
                
                return None
                
    except Exception as e:
        print(f"⚠️ Error extracting transfer signature: {e}")
        return None


# --- Kelas Bot Discord ---
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Whitelist server yang diizinkan
ALLOWED_GUILDS = [
    1411612828867100684,  # Abuyy's server
    1445079009405833299,  # BLOX
]

class MyClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        """Called when the bot is starting"""
        # Register persistent view untuk button
        self.add_view(CreateTicketButton())
        self.add_view(CreateMiddlemanButton())
        # Start auto-backup task
        self.auto_backup_task.start()
        # Start auto-update leaderboard task
        self.auto_update_leaderboard.start()
    
    async def on_ready(self):
        print(f'✅ Bot berhasil Login sebagai {self.user} (ID: {self.user.id})')
        print(f"📡 Bot aktif di {len(self.guilds)} server")
        for guild in self.guilds:
            print(f"   - {guild.name} (ID: {guild.id})")
            # Auto-leave jika bukan server yang diizinkan
            if guild.id not in ALLOWED_GUILDS:
                print(f"⚠️ Server {guild.name} tidak ada di whitelist, keluar...")
                await guild.leave()
                print(f"✅ Bot keluar dari server {guild.name}")
        print("⏳ Mencoba sinkronisasi Slash Commands...")
        try:
            # Global sync
            synced = await self.tree.sync()
            print(f"🎉 {len(synced)} Slash Commands synced globally!")
            print("💡 Commands sekarang tersedia di semua server!")
        except Exception as e:
            print(f"❌ Gagal sinkronisasi commands: {e}")
    
    @tasks.loop(hours=24)
    async def auto_backup_task(self):
        """Auto-backup setiap 24 jam"""
        try:
            print("🔄 Menjalankan auto-backup...")
            # Backup untuk setiap guild
            backup_dir = os.path.join(DATA_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup semua guilds
            for guild in self.guilds:
                all_stats = db.get_all_user_stats(guild.id)
                if not all_stats:
                    continue
                    
                backup_data = {
                    stat['user_id']: {
                        'deals_completed': stat['deals_completed'],
                        'total_idr_value': stat['total_idr_value']
                    }
                    for stat in all_stats
                }
            
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                backup_file = os.path.join(backup_dir, f'auto_backup_{guild.id}_{timestamp}.json')
                
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)
                
                print(f"✅ Auto-backup selesai untuk {guild.name}: {backup_file}")
            
            # Hapus backup lama (simpan hanya 30 backup terakhir)
            files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.startswith('auto_backup_')]
            files.sort(key=os.path.getmtime, reverse=True)
            for old_file in files[30:]:
                try:
                    os.remove(old_file)
                    print(f"🗑️ Hapus backup lama: {old_file}")
                except:
                    pass
        except Exception as e:
            print(f"❌ Error saat auto-backup: {e}")
    
    @auto_backup_task.before_loop
    async def before_auto_backup(self):
        """Wait until bot is ready"""
        await self.wait_until_ready()
    
    @tasks.loop(hours=2)
    async def auto_update_leaderboard(self):
        """Auto-update leaderboard di #lb-rich-daily setiap 2 jam"""
        try:
            for guild in self.guilds:
                # Cek apakah ada message leaderboard yang tersimpan
                lb_data = db.get_leaderboard_message(guild.id)
                
                if not lb_data:
                    # Belum ada message, skip
                    continue
                
                try:
                    # Ambil channel
                    channel = guild.get_channel(lb_data['channel_id'])
                    if not channel:
                        continue
                    
                    # Hapus message lama
                    try:
                        old_message = await channel.fetch_message(lb_data['message_id'])
                        await old_message.delete()
                    except discord.NotFound:
                        pass  # Message sudah dihapus
                    
                    # Generate leaderboard embed terbaru
                    embed = await self.generate_leaderboard_embed(guild)
                    
                    # Post message baru
                    new_message = await channel.send(embed=embed)
                    
                    # Update message ID di database
                    db.set_leaderboard_message(guild.id, channel.id, new_message.id)
                    
                    print(f"✅ Leaderboard auto-updated untuk {guild.name}")
                    
                except Exception as e:
                    print(f"❌ Error update leaderboard {guild.name}: {e}")
                    
        except Exception as e:
            print(f"❌ Error auto-update leaderboard: {e}")
    
    @auto_update_leaderboard.before_loop
    async def before_auto_update_leaderboard(self):
        """Wait until bot is ready"""
        await self.wait_until_ready()
    
    async def generate_leaderboard_embed(self, guild: discord.Guild) -> discord.Embed:
        """Generate embed untuk leaderboard"""
        from datetime import datetime as dt, timedelta
        
        # Ambil top 10 weekly stats
        weekly_stats = db.get_weekly_leaderboard(guild.id, limit=10)
        
        # Get week info
        week_start = db.get_current_week_start()
        week_start_dt = dt.strptime(week_start, '%Y-%m-%d')
        week_end_dt = week_start_dt + timedelta(days=6)
        
        # Buat embed
        embed = discord.Embed(
            title="",
            description="",
            color=0xFFD700,
            timestamp=dt.now()
        )
        
        embed.set_author(
            name="👑 Weekly Leaderboard — Top Sultan",
            icon_url=guild.icon.url if guild.icon else None
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Ranking icons - attractive for top 3, uniform for 4-10
        ranking_emoji = {
            1: "👑",  # Crown for #1
            2: "🌟",  # Star for #2
            3: "💎"   # Diamond for #3
        }
        
        if not weekly_stats:
            embed.description = (
                f"🏆 **Top 10 Sultan**\n\n"
                "Belum ada transaksi minggu ini."
            )
        else:
            leaderboard_text = []
            for idx, stat in enumerate(weekly_stats, 1):
                try:
                    member = await guild.fetch_member(int(stat['user_id']))
                    name = member.display_name
                except:
                    name = f"User {stat['user_id']}"
                
                # Top 3 get special icons, 4-10 get uniform numbering
                if idx <= 3:
                    rank_emoji = ranking_emoji[idx]
                else:
                    rank_emoji = f"▫️ `#{idx}`"
                leaderboard_text.append(
                    f"{rank_emoji} **{name}** `Top {idx}`\n"
                    f"   **{stat['deals_count']}** transaksi • 💵 {format_idr(stat['weekly_spend'])}"
                )
            
            embed.description = (
                f"🏆 **Top {len(weekly_stats)} Sultan**\n\n" +
                "\n\n".join(leaderboard_text)
            )
        
        # Footer dengan info reset
        next_monday = week_start_dt + timedelta(days=7)
        days_until_reset = (next_monday - dt.now()).days
        footer_text = f"🔄 Auto-update setiap 2 jam • Reset: {days_until_reset} hari lagi"
        
        embed.set_footer(text=footer_text, icon_url=guild.icon.url if guild.icon else None)
        
        return embed
    
    async def on_guild_join(self, guild: discord.Guild):
        """Event ketika bot di-invite ke server baru"""
        if guild.id not in ALLOWED_GUILDS:
            print(f"⚠️ Bot di-invite ke server tidak diizinkan: {guild.name} (ID: {guild.id})")
            print(f"✅ Bot otomatis keluar dari {guild.name}")
            await guild.leave()
    
    async def on_member_join(self, member: discord.Member):
        """Event ketika ada member baru join server"""
        try:
            # Cari role "Guest"
            guest_role = discord.utils.get(member.guild.roles, name="Guest")
            
            if guest_role:
                await member.add_roles(guest_role)
                print(f"✅ Auto-role 'Guest' diberikan ke {member.name}")
            else:
                print(f"⚠️ Role 'Guest' tidak ditemukan di server {member.guild.name}")
            
            # Send welcome message ke #welcome dengan design estetik
            welcome_channel = discord.utils.get(member.guild.text_channels, name="welcome")
            if welcome_channel:
                # Cari channel #open-ticket untuk mention
                open_ticket_channel = discord.utils.get(member.guild.text_channels, name="open-ticket")
                # Format channel mention dengan benar
                if open_ticket_channel:
                    channel_mention = open_ticket_channel.mention
                else:
                    # Jika channel tidak ada, gunakan text biasa tanpa #
                    channel_mention = "channel **open-ticket**"
                
                # Embed estetik dengan gradient color
                welcome_embed = discord.Embed(
                    description=f"## 🌟 Welcome to **{member.guild.name}**! 🌟\n\n"
                                f"Halo {member.mention}! Kami senang kamu bergabung! ✨",
                    color=0x00D9FF,  # Cyan estetik
                    timestamp=datetime.now()
                )
                
                # Set thumbnail (avatar member) ukuran kecil di pojok
                welcome_embed.set_thumbnail(url=member.display_avatar.url)
                
                # Author dengan server icon
                if member.guild.icon:
                    welcome_embed.set_author(
                        name=f"{member.guild.name}",
                        icon_url=member.guild.icon.url
                    )
                
                # Field dengan emoji dan spacing bagus
                welcome_embed.add_field(
                    name="🎯 Mulai Petualangan Kamu",
                    value=f"📌 Buka {channel_mention}\n📋 Buat ticket pembelian\n🎁 Nikmati layanan terbaik!",
                    inline=False
                )
                
                welcome_embed.add_field(
                    name="👥 Komunitas",
                    value=f"```\nKamu adalah member ke-{member.guild.member_count}\n```",
                    inline=True
                )
                
                welcome_embed.add_field(
                    name="🎊 Status",
                    value=f"```\nRole: Guest\n```",
                    inline=True
                )
                
                # Footer estetik
                welcome_embed.set_footer(
                    text=f"Welcome • {member.name}",
                    icon_url=member.display_avatar.url
                )
                
                await welcome_channel.send(embed=welcome_embed)
        except Exception as e:
            print(f"❌ Error di on_member_join: {e}")
    
    async def on_member_remove(self, member: discord.Member):
        """Event ketika ada member keluar/kicked/banned dari server"""
        try:
            # Send goodbye message ke #good-bye dengan design estetik
            goodbye_channel = discord.utils.get(member.guild.text_channels, name="good-bye")
            if goodbye_channel:
                # Embed estetik dengan dark elegant color
                goodbye_embed = discord.Embed(
                    description=f"## 💫 Farewell, **{member.name}** 💫\n\n"
                                f"Seseorang telah meninggalkan server...",
                    color=0xFF6B9D,  # Pink soft estetik
                    timestamp=datetime.now()
                )
                
                # Set thumbnail (avatar member) ukuran kecil di pojok
                goodbye_embed.set_thumbnail(url=member.display_avatar.url)
                
                # Author dengan server icon
                if member.guild.icon:
                    goodbye_embed.set_author(
                        name=f"{member.guild.name}",
                        icon_url=member.guild.icon.url
                    )
                
                # Field dengan design menarik
                goodbye_embed.add_field(
                    name="👋 Sampai Jumpa",
                    value=f"```\n💭 {member.name} telah pergi\n💝 Terima kasih atas kebersamaannya\n🌈 Semoga kita bertemu lagi!\n```",
                    inline=False
                )
                
                goodbye_embed.add_field(
                    name="📊 Member Tersisa",
                    value=f"```\n{member.guild.member_count} Members\n```",
                    inline=True
                )
                
                goodbye_embed.add_field(
                    name="⏰ Waktu",
                    value=f"```\n{datetime.now().strftime('%d %b %Y')}\n```",
                    inline=True
                )
                
                # Footer estetik
                goodbye_embed.set_footer(
                    text=f"Goodbye • We'll miss you",
                    icon_url=member.display_avatar.url
                )
                
                await goodbye_channel.send(embed=goodbye_embed)
                print(f"👋 Goodbye message sent for {member.name}")
        except Exception as e:
            print(f"❌ Error di on_member_remove: {e}")

    async def on_guild_channel_delete(self, channel: discord.TextChannel):
        """Auto-close ticket ketika channel dihapus manual"""
        try:
            # Cek apakah channel ini adalah ticket channel
            ticket = db.get_ticket_by_channel(channel.id)
            
            if ticket and ticket['status'] == 'open':
                # Auto-close ticket
                db.close_ticket(ticket['id'], closed_by=0)  # 0 = auto-closed
                print(f"✅ Auto-closed ticket #{ticket['ticket_number']:04d} (channel deleted: {channel.name})")
        except Exception as e:
            print(f"❌ Error in on_guild_channel_delete: {e}")
    
    async def on_message(self, message: discord.Message):
        # Skip DM messages
        if not message.guild:
            return
        
        # Ignore bot messages untuk processing lainnya
        if message.author.bot:
            return
        
        # Hanya proses jika ada guild
        if not message.guild:
            return
        
        # ===== AUTO-DETECT BUKTI TRANSFER DI TICKET CHANNEL =====
        # Cek apakah ini ticket channel dan ada attachment gambar
        ticket = db.get_ticket_by_channel(message.channel.id)
        
        if ticket and ticket['status'] == 'open' and message.attachments:
            # Check ticket type
            is_middleman = ticket.get('ticket_type') == 'middleman'
            buyer_id = int(ticket['user_id'])
            seller_id = int(ticket.get('seller_id')) if ticket.get('seller_id') else None
            
            # Cek apakah ada attachment gambar
            for attachment in message.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    # MIDDLEMAN TICKET: Handle both buyer and seller proof
                    if is_middleman:
                        # Buyer uploading proof
                        if message.author.id == buyer_id:
                            await self.process_proof_submission(message, ticket, attachment.url, proof_type='buyer')
                            break
                        # Seller uploading proof
                        elif seller_id and message.author.id == seller_id:
                            await self.process_proof_submission(message, ticket, attachment.url, proof_type='seller')
                            break
                    # PURCHASE TICKET: Only buyer proof
                    else:
                        if message.author.id == buyer_id:
                            await self.process_proof_submission(message, ticket, attachment.url)
                            break
        
        # Cek guild config untuk auto-detect channels
        guild_config = db.get_guild_config(message.guild.id)
        auto_channels = guild_config.get('auto_detect_channels', [])
        
        # Jika auto_channels kosong, aktif di semua channel. Jika ada list, cek channel ini ada di list
        if auto_channels and str(message.channel.id) not in auto_channels:
            return
        
        # Gunakan regex dari config
        regex_pattern = guild_config.get('auto_detect_regex', r"transaksi\s*(?:selesai)?[:\s]+([\d\.,]+)")
        m = re.search(regex_pattern, message.content, re.IGNORECASE)
        if not m:
            return

        raw_amount = m.group(1)
        # Hapus titik/komma non-digit
        amount_digits = re.sub(r"[^0-9]", "", raw_amount)
        if not amount_digits:
            return
        try:
            amount = int(amount_digits)
        except Exception:
            return

        # Update stats untuk author menggunakan database
        updated = db.update_user_stats(message.guild.id, message.author.id, amount)
        db.add_transaction(message.guild.id, message.author.id, amount, category="auto_detect", notes=f"Auto-detected from message", recorded_by=None)
        
        # Cek achievement baru
        new_achievements = db.check_and_unlock_achievement(message.guild.id, message.author.id)
        
        # Log activity
        db.log_action(message.guild.id, message.author.id, "auto_detect_transaction", f"Amount: {amount}")

        # Kirim konfirmasi
        try:
            msg = (
                f"✅ Statistik untuk **{message.author.display_name}** diperbarui: "
                f"Total Transaksi: **{updated.get('deals_completed',0)}**, "
                f"Total IDR: **{format_idr(updated.get('total_idr_value',0))}**"
            )
            
            # Tambahkan achievement baru jika ada
            if new_achievements:
                achievement_names = {
                    'deals_10': '🎯 10 Transaksi',
                    'deals_50': '🔥 50 Transaksi',
                    'deals_100': '⭐ 100 Transaksi',
                    'deals_500': '💎 500 Transaksi',
                    'value_1m': '💰 Rp1 Juta',
                    'value_5m': '💸 Rp5 Juta',
                    'value_10m': '🏆 Rp10 Juta',
                    'value_50m': '👑 Rp50 Juta',
                }
                achievement_text = ", ".join([achievement_names.get(a, a) for a in new_achievements])
                msg += f"\n🎉 **Achievement Baru Unlocked!** {achievement_text}"
            
            await message.channel.send(msg)
        except Exception:
            pass
    
    async def process_proof_submission(self, message: discord.Message, ticket: dict, proof_url: str, proof_type: str = 'buyer'):
        """Process auto-detected proof submission from image upload
        
        Args:
            message: Discord message object
            ticket: Ticket dictionary from database
            proof_url: URL of the uploaded image
            proof_type: 'buyer' for buyer payment proof, 'seller' for seller delivery proof
        """
        try:
            print(f"\n{'='*60}")
            print(f"🔍 PROCESSING {proof_type.upper()} PROOF: Ticket #{ticket['ticket_number']:04d}")
            print(f"{'='*60}")
            
            # === SELLER PROOF (Simpler validation) ===
            if proof_type == 'seller':
                print("📦 Processing seller delivery proof...")
                
                # Run basic fraud detection (no transfer signature needed)
                legitimate_check = await detect_legitimate_transfer_screenshot(proof_url)
                manipulation_result = await detect_image_manipulation(proof_url)
                
                if manipulation_result['manipulation_detected'] and manipulation_result['confidence'] > 60:
                    await message.channel.send(
                        f"{message.author.mention}\n"
                        "🚨 **GAMBAR MENCURIGAKAN TERDETEKSI!**\n\n"
                        f"❌ Gambar terdeteksi manipulasi (confidence: {manipulation_result['confidence']:.1f}%)\n\n"
                        "⚠️ Upload screenshot/bukti ASLI tanpa edit!"
                    )
                    await message.add_reaction("❌")
                    return
                
                # Save seller proof
                db.update_seller_proof(ticket['id'], proof_url)
                
                # Send confirmation
                seller_embed = discord.Embed(
                    title="📦 Bukti Pengiriman Diterima",
                    description=f"{message.author.mention} telah upload bukti pengiriman item.",
                    color=0xFFA500,
                    timestamp=datetime.now()
                )
                
                seller_embed.add_field(
                    name="🎫 Ticket ID",
                    value=f"`#{ticket['ticket_number']:04d}`",
                    inline=True
                )
                
                seller_embed.add_field(
                    name="📦 Item",
                    value=f"`{ticket.get('item_description', 'N/A')}`",
                    inline=True
                )
                
                seller_embed.add_field(
                    name="💰 Deal Price",
                    value=f"**Rp{ticket.get('deal_price', 0):,}**",
                    inline=True
                )
                
                seller_embed.add_field(
                    name="🔗 Bukti Seller",
                    value=f"[📸 Klik untuk melihat]({proof_url})",
                    inline=False
                )
                
                seller_embed.add_field(
                    name="⚙️ Next Step",
                    value="Admin akan verifikasi dan release dana ke seller.\nGunakan `/approve-mm` untuk approve transaksi.",
                    inline=False
                )
                
                seller_embed.set_footer(
                    text="⏳ Waiting admin approval | Middleman Transaction",
                    icon_url=message.guild.icon.url if message.guild.icon else None
                )
                
                # Get admin mentions
                guild_config = db.get_guild_config(message.guild.id)
                admin_roles = guild_config.get('admin_roles', [])
                owner = message.guild.owner
                
                admin_mentions = [owner.mention]
                for role_id in admin_roles:
                    role = message.guild.get_role(int(role_id))
                    if role:
                        admin_mentions.append(role.mention)
                
                mention_text = " ".join(admin_mentions)
                
                await message.channel.send(
                    f"🔔 {mention_text}\n\n"
                    f"📦 **SELLER PROOF RECEIVED!**\n"
                    f"Ticket #{ticket['ticket_number']:04d} - Seller telah upload bukti pengiriman.\n\n"
                    f"Silakan verifikasi dan gunakan `/approve-mm` untuk release dana.",
                    embed=seller_embed
                )
                
                await message.add_reaction("✅")
                print(f"✅ Seller proof saved successfully")
                return
            
            # === BUYER PROOF (Full 4-Layer Fraud Detection) ===
            print("💰 Processing buyer payment proof with 4-Layer Fraud Detection...")
            
            # === LAYER 1: TRANSFER SIGNATURE CHECK (Account + Date + Amount) ===
            print("📝 Layer 1: Extracting transfer signature...")
            transfer_signature = await extract_transfer_signature(proof_url)
            
            if transfer_signature:
                print(f"✅ Transfer signature: {transfer_signature}")
                # Check exact match by transfer signature
                exact_duplicate = db.check_duplicate_proof(
                    guild_id=message.guild.id,
                    transfer_signature=transfer_signature
                )
                
                if exact_duplicate:
                    print(f"🚨 LAYER 1 FRAUD DETECTED: Signature match with Ticket #{exact_duplicate['ticket_number']:04d}")
                    # EXACT SAME TRANSFER DETECTED (same account, date, amount)
                    duplicate_user = await message.guild.fetch_member(int(exact_duplicate['user_id']))
                    
                    await message.channel.send(
                        f"{message.author.mention}\n"
                        "🚨 **TRANSFER YANG SAMA TERDETEKSI!**\n\n"
                        f"❌ Transfer dengan **rekening, tanggal, dan nominal yang sama** sudah digunakan di:\n"
                        f"• **Ticket:** `#{exact_duplicate['ticket_number']:04d}`\n"
                        f"• **User:** {duplicate_user.mention if duplicate_user else 'Unknown'}\n"
                        f"• **Username:** `{exact_duplicate['game_username']}`\n"
                        f"• **Tanggal:** {exact_duplicate['created_at']}\n"
                        f"• **Status:** `{exact_duplicate['status']}`\n\n"
                        "⚠️ **Gunakan screenshot ASLI dari transfer Anda!**\n"
                        "Setiap transaksi harus menggunakan bukti transfer yang berbeda.\n\n"
                        f"*(Transfer Signature: {transfer_signature[:30]}...)*"
                    )
                    
                    await message.channel.send(
                        f"🚨 **FRAUD ALERT:** {message.author.mention} mencoba submit transfer yang sama dengan Ticket #{exact_duplicate['ticket_number']:04d}"
                    )
                    return
                else:
                    print("✅ No signature duplicates found")
            else:
                print("⚠️ Could not extract transfer signature (OCR unavailable or failed)")
            
            # === LAYER 1.5: SMART FRAUD DETECTION (Whitelist + Manipulation) ===
            print("\n🔍 Layer 1.5: Checking screenshot legitimacy...")
            
            # STEP 1: Check if screenshot is from known legitimate source
            legitimate_check = await detect_legitimate_transfer_screenshot(proof_url)
            
            if legitimate_check['is_legitimate']:
                print(f"✅ WHITELISTED: {legitimate_check['source']} (confidence: {legitimate_check['confidence']:.1f}%)")
                print("   ⏭️  Skipping manipulation detection for legitimate banking app screenshot")
                # BYPASS manipulation detection - proceed directly to next layer
            else:
                # STEP 2: Screenshot source unclear, run manipulation detection
                print(f"⚠️ Unknown source (confidence: {legitimate_check['confidence']:.1f}%) - running manipulation check...")
                manipulation_result = await detect_image_manipulation(proof_url)
                
                if manipulation_result['manipulation_detected']:
                    print(f"🚨 LAYER 1.5 FRAUD: Image manipulation detected!")
                    
                    # Build warning message
                    warning_list = "\n".join([f"   {w}" for w in manipulation_result['warnings']])
                    
                    await message.channel.send(
                        f"{message.author.mention}\n"
                        "🚨 **GAMBAR MENCURIGAKAN TERDETEKSI!**\n\n"
                        f"❌ Sistem mendeteksi **manipulasi gambar** dengan confidence **{manipulation_result['confidence']:.1f}%**:\n\n"
                        f"{warning_list}\n\n"
                        "⚠️ **PERINGATAN:**\n"
                        "• Screenshot transfer **TIDAK BOLEH** diedit/dicoret\n"
                        "• Gunakan screenshot **ASLI** dari aplikasi banking/e-wallet\n"
                        "• **Admin akan REJECT** bukti transfer yang diedit!\n\n"
                        "💡 **Gunakan screenshot dari:**\n"
                        "• BCA Mobile, Mandiri Online, BRI Mobile\n"
                        "• GoPay, OVO, Dana, ShopeePay\n"
                        "• Bank lainnya (screenshot asli tanpa edit)\n\n"
                        "Silakan upload ulang bukti transfer yang ASLI."
                    )
                    
                    await message.channel.send(
                        f"🚨 **MANIPULATION ALERT:** {message.author.mention} upload bukti transfer dengan manipulasi (confidence: {manipulation_result['confidence']:.1f}%)"
                    )
                    
                    # CRITICAL: HARD BLOCK - Stop processing immediately!
                    # DO NOT save to database, DO NOT send confirmation embed
                    await message.add_reaction("❌")
                    print("🚫 Processing stopped due to image manipulation detection")
                    return  # STOP HERE - No further processing!
            
            # === LAYER 2: PERCEPTUAL HASH CHECK (Image Similarity) ===
            print("\n🎨 Layer 2: Generating perceptual hash...")
            print(f"   Image URL: {proof_url[:80]}...")
            proof_hash = await get_image_hash(proof_url)
            
            if proof_hash:
                print(f"   ✅ Hash generated successfully!")
                print(f"   dhash: {proof_hash['dhash'][:16]}...")
                print(f"   phash: {proof_hash['phash'][:16]}...")
                print(f"   ahash: {proof_hash['ahash'][:16]}...")
                print(f"   combined: {proof_hash['combined'][:50]}...")
                
                # CRITICAL FIX: Save hash FIRST before checking (so we have data to compare)
                print(f"💾 Saving hashes to database...")
                print(f"   Ticket ID: {ticket['id']}")
                print(f"   Transfer signature: {transfer_signature[:30] if transfer_signature else 'None'}...")
                db.save_proof_hash(ticket['id'], proof_hash['combined'], transfer_signature)
                print("✅ Hashes saved successfully")
                
                # Now check similarity (will compare with OTHER tickets, excluding current one)
                print(f"\n🔍 Multi-algorithm similarity check...")
                print(f"   Current ticket ID to EXCLUDE: {ticket['id']}")
                print(f"   Guild ID: {message.guild.id}")
                duplicate = await check_similar_images(
                    message.guild.id, 
                    proof_hash,
                    current_ticket_id=ticket['id']
                )
                print(f"   Duplicate result: {duplicate}")
                
                if duplicate:
                    # Check if this is SAME ticket (user trying to upload same image again)
                    if duplicate.get('is_same_ticket'):
                        print(f"🚨 LAYER 2 FRAUD: User trying to upload SAME image to SAME ticket!")
                        await message.channel.send(
                            f"{message.author.mention}\n"
                            "🚨 **GAMBAR SAMA TERDETEKSI!**\n\n"
                            f"❌ Anda **sudah upload gambar ini** ke ticket ini sebelumnya!\n"
                            f"• **Similarity:** {duplicate['similarity']}\n\n"
                            "⚠️ **Tidak boleh upload gambar yang sama 2x!**\n"
                            "Jika ingin ganti bukti transfer, upload **screenshot yang BERBEDA**.\n\n"
                            f"*(Detected via {duplicate['algorithm']} | {duplicate['all_distances']})*"
                        )
                        await message.add_reaction("❌")
                        return
                    
                    # Different ticket - fraud attempt
                    print(f"🚨 LAYER 2 FRAUD DETECTED: Image similarity with Ticket #{duplicate['ticket_number']:04d}")
                    # Gambar similar terdeteksi
                    duplicate_user = await message.guild.fetch_member(int(duplicate['user_id']))
                    
                    await message.channel.send(
                        f"{message.author.mention}\n"
                        "🚨 **GAMBAR SERUPA TERDETEKSI!**\n\n"
                        f"❌ Screenshot ini **{duplicate['similarity']} mirip** dengan gambar di:\n"
                        f"• **Ticket:** `#{duplicate['ticket_number']:04d}`\n"
                        f"• **User:** {duplicate_user.mention if duplicate_user else 'Unknown'}\n"
                        f"• **Username:** `{duplicate['game_username']}`\n"
                        f"• **Tanggal:** {duplicate['created_at']}\n"
                        f"• **Status:** `{duplicate['status']}`\n\n"
                        "⚠️ **Gunakan screenshot ASLI dari transfer Anda!**\n"
                        "Bukti transfer harus unik untuk setiap transaksi.\n\n"
                        f"*(Detected via {duplicate['algorithm']} | {duplicate['all_distances']})*"
                    )
                    
                    await message.channel.send(
                        f"⚠️ **FRAUD ALERT:** {message.author.mention} mencoba submit gambar mirip ({duplicate['similarity']}) dengan Ticket #{duplicate['ticket_number']:04d}"
                    )
                    return
                else:
                    print("✅ No similar images found")
            
            # Ambil data items
            items = db.get_ticket_items(ticket['id'])
            if not items:
                await message.channel.send(
                    f"{message.author.mention} ❌ Belum ada item di ticket ini. Gunakan `/add` terlebih dahulu."
                )
                return
            
            grand_total = sum(i['amount'] for i in items)
            
            # ===== LAYER 3: OCR AMOUNT DETECTION =====
            detected_amount = await extract_amount_from_image(proof_url)
            amount_warning = None
            
            if detected_amount:
                # Compare detected amount with expected total
                tolerance = 1000  # Allow Rp1.000 difference (for fees, etc)
                diff = abs(detected_amount - grand_total)
                
                if diff > tolerance:
                    # Amount mismatch detected!
                    amount_warning = (
                        f"⚠️ **PERINGATAN NOMINAL TIDAK SESUAI!**\n"
                        f"• **Terdeteksi di Screenshot:** {format_idr(detected_amount)}\n"
                        f"• **Yang Seharusnya:** {format_idr(grand_total)}\n"
                        f"• **Selisih:** {format_idr(diff)}\n\n"
                        f"🚨 Admin harap **CEK ULANG** bukti transfer ini!"
                    )
            
            # Buat embed bukti transfer
            submit_embed = discord.Embed(
                title="📨 Bukti Transfer Diterima",
                description=f"{message.author.mention} telah mengirimkan bukti pembayaran untuk diverifikasi.",
                color=0xE67E22 if amount_warning else 0x1ABC9C,  # Orange if warning, green if ok
                timestamp=datetime.now()
            )
            
            submit_embed.add_field(name="🎫 Ticket ID", value=f"`#{ticket['ticket_number']:04d}`", inline=True)
            submit_embed.add_field(name="👤 Username", value=f"`{ticket['game_username']}`", inline=True)
            submit_embed.add_field(name="💳 Total", value=f"**{format_idr(grand_total)}**", inline=True)
            
            items_list = []
            for i in items:
                items_list.append(f"`{i['item_name']}` — {format_idr(i['amount'])}")
            
            submit_embed.add_field(
                name="📦 Detail Order",
                value="\n".join(items_list),
                inline=False
            )
            
            # Add OCR detection info if available
            if detected_amount:
                ocr_status = "✅ Sesuai" if not amount_warning else f"❌ TIDAK SESUAI (Rp{detected_amount:,})"
                submit_embed.add_field(
                    name="🤖 Auto-Detect Nominal",
                    value=ocr_status,
                    inline=False
                )
            
            # Add transfer signature if detected
            if transfer_signature:
                submit_embed.add_field(
                    name="🔐 Transfer Signature",
                    value=f"`{transfer_signature[:40]}...`",
                    inline=False
                )
            
            submit_embed.add_field(
                name="🔗 Bukti Transfer",
                value=f"[📸 Klik untuk melihat bukti]({proof_url})",
                inline=False
            )
            
            submit_embed.add_field(
                name="⚙️ Admin Panel",
                value="✅ `/approve-ticket` — Setujui transaksi\n❌ `/reject-ticket` — Tolak transaksi",
                inline=False
            )
            
            submit_embed.set_footer(
                text="⏳ Menunggu verifikasi admin | 4-Layer Fraud Detection", 
                icon_url=message.guild.icon.url if message.guild.icon else None
            )
            
            # Save ke database
            db.update_ticket_proof(ticket['id'], proof_url)
            if proof_hash:
                db.save_proof_hash(ticket['id'], proof_hash['combined'], transfer_signature)
            
            # Update mm_status if middleman ticket
            if ticket.get('ticket_type') == 'middleman':
                db.update_mm_status(ticket['id'], 'waiting_item_delivery')
            
            # GET ADMIN & OWNER untuk TAG
            guild_config = db.get_guild_config(message.guild.id)
            admin_roles = guild_config.get('admin_roles', [])
            owner = message.guild.owner
            
            admin_mentions = []
            for role_id in admin_roles:
                role = message.guild.get_role(int(role_id))
                if role:
                    admin_mentions.append(role.mention)
            
            # Mention admin & owner
            mention_text = f"{owner.mention} "
            if admin_mentions:
                mention_text += " ".join(admin_mentions)
            
            # Determine command based on ticket type
            is_middleman = ticket.get('ticket_type') == 'middleman'
            approve_cmd = "/approve-mm" if is_middleman else "/approve-ticket"
            reject_cmd = "/reject-mm" if is_middleman else "/reject-ticket"
            
            # SEND dengan TAG ADMIN & OWNER
            await message.channel.send(
                f"🔔 {mention_text}\n\n"
                f"✅ **BUKTI TRANSFER BERHASIL TERDETEKSI!**\n"
                f"📌 Ticket #{ticket['ticket_number']:04d} - {message.author.mention}\n"
                f"💰 Total: **{format_idr(grand_total)}**\n\n"
                f"⚡ Fraud Detection: **PASSED** (All Layers)\n"
                f"🤖 Screenshot: **LEGITIMATE** (Confidence: {legitimate_check['confidence']:.1f}%)\n\n"
                f"Admin harap verifikasi menggunakan:\n"
                f"• ✅ `{approve_cmd}` — Approve transaksi\n"
                f"• ❌ `{reject_cmd}` — Reject transaksi",
                embed=submit_embed
            )
            
            # Send warning message if amount mismatch
            if amount_warning:
                await message.channel.send(
                    f"⚠️ {mention_text}\n\n{amount_warning}"
                )
                await message.add_reaction("⚠️")
            else:
                await message.add_reaction("✅")  # React checkmark ke gambar yang diupload
            
        except Exception as e:
            print(f"❌ Error processing auto-proof: {e}")
            import traceback
            traceback.print_exc()
            await message.channel.send(
                f"{message.author.mention} ❌ Gagal memproses bukti transfer otomatis. Coba upload ulang screenshot."
            )

# Inisialisasi Klien Bot
client = MyClient(intents=intents)


# --- Slash Command: /reset_stats ---
@client.tree.command(
    name="reset_stats",
    description="[OWNER] Reset Total Transaksi dan Total Spend untuk user atau semua user."
)
@app_commands.describe(
    user='User yang ingin di-reset (default: diri sendiri)',
    reset_all='Jika true, reset semua user'
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def reset_stats(interaction: discord.Interaction, user: Optional[discord.Member] = None, reset_all: Optional[bool] = False):
    await interaction.response.defer(ephemeral=True)

    if reset_all:
        # Jangan langsung reset — kirim konfirmasi dengan tombol dan buat backup saat dikonfirmasi
        class ResetAllConfirmView(discord.ui.View):
            def __init__(self, initiator_id: int, timeout: int = 60):
                super().__init__(timeout=timeout)
                self.initiator_id = initiator_id

            @discord.ui.button(label="Konfirmasi Reset Semua", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                # Hanya peminta atau owner yang boleh mengkonfirmasi
                try:
                    allowed = (interaction_btn.user.id == self.initiator_id) or is_owner(interaction_btn)
                except Exception:
                    allowed = False
                if not allowed:
                    await interaction_btn.response.send_message("❌ Anda tidak diizinkan melakukan aksi ini.", ephemeral=True)
                    return

                # Backup current data dari database
                all_stats = db.get_all_user_stats(interaction_btn.guild.id)
                backup_data = {
                    stat['user_id']: {
                        'deals_completed': stat['deals_completed'],
                        'total_idr_value': stat['total_idr_value']
                    }
                    for stat in all_stats
                }
                
                ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
                backup_dir = os.path.join(DATA_DIR, 'backups')
                os.makedirs(backup_dir, exist_ok=True)
                backup_file = os.path.join(backup_dir, f'user_data_backup_{ts}.json')
                try:
                    with open(backup_file, 'w', encoding='utf-8') as bf:
                        json.dump(backup_data, bf, ensure_ascii=False, indent=2)
                except Exception as e:
                    await interaction_btn.response.send_message(f"❌ Gagal membuat backup: {e}", ephemeral=True)
                    return

                # Clear data menggunakan database
                try:
                    db.reset_all_stats(interaction_btn.guild.id)
                    db.log_action(interaction_btn.guild.id, interaction_btn.user.id, "reset_all_stats", f"Backup: {backup_file}")
                except Exception as e:
                    await interaction_btn.response.send_message(f"❌ Gagal mereset data: {e}", ephemeral=True)
                    return

                # Disable buttons and edit original message
                for child in list(self.children):
                    child.disabled = True
                try:
                    await interaction_btn.message.edit(content=f"✅ Semua statistik telah di-reset oleh **{interaction_btn.user.display_name}**. Backup disimpan: `{os.path.relpath(backup_file)}`", view=self)
                except Exception:
                    pass
                await interaction_btn.response.send_message("✅ Reset selesai dan backup dibuat.", ephemeral=True)

                # Kirim DM ke semua admin di guild agar mereka tahu backup dibuat
                try:
                    guild = interaction_btn.guild or await client.fetch_guild(SERVER_ID)
                    # Prefer fetch_members if available to ensure full member list
                    members = []
                    try:
                        members = [m async for m in guild.fetch_members(limit=None)]
                    except Exception:
                        members = guild.members

                    for m in members:
                        try:
                            if m.bot:
                                continue
                            if hasattr(m, 'guild_permissions') and m.guild_permissions.administrator:
                                try:
                                    await m.send(f"🔔 Backup data user telah dibuat oleh **{interaction_btn.user.display_name}**. File backup: `{os.path.relpath(backup_file)}`")
                                except Exception:
                                    # jika gagal kirim DM (DM tertutup), skip
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass

            @discord.ui.button(label="Batal", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                # Only initiator or admin may cancel
                try:
                    allowed = (interaction_btn.user.id == self.initiator_id) or interaction_btn.user.guild_permissions.administrator
                except Exception:
                    allowed = False
                if not allowed:
                    await interaction_btn.response.send_message("❌ Anda tidak diizinkan membatalkan aksi ini.", ephemeral=True)
                    return
                for child in list(self.children):
                    child.disabled = True
                try:
                    await interaction_btn.message.edit(content="❌ Reset dibatalkan.", view=self)
                except Exception:
                    pass
                await interaction_btn.response.send_message("✅ Reset dibatalkan.", ephemeral=True)

        view = ResetAllConfirmView(initiator_id=interaction.user.id)
        await interaction.response.send_message("⚠️ Anda berusaha mereset semua statistik. Tekan **Konfirmasi Reset Semua** untuk membuat backup lalu melanjutkan.", view=view, ephemeral=False)
        return

    # Reset single user (default: self)
    target = user if user is not None else interaction.user
    # Owner bisa reset siapa saja, user biasa hanya diri sendiri
    if target.id != interaction.user.id and not is_owner(interaction):
        await interaction.followup.send("❌ Anda hanya dapat mereset statistik diri sendiri.", ephemeral=True)
        return

    # Reset menggunakan database
    db.reset_user_stats(interaction.guild.id, target.id)
    
    # Log action
    db.log_action(interaction.guild.id, interaction.user.id, "reset_user_stats", f"Target: {target.id}")

    await interaction.followup.send(f"✅ Statistik untuk **{target.display_name}** telah di-reset.", ephemeral=False)


@client.tree.command(
    name="reset-tickets",
    description="[ADMIN] Hapus tickets user tertentu."
)
@app_commands.describe(user='User yang ticketnya akan dihapus')
@app_commands.default_permissions(administrator=True)
async def reset_tickets(interaction: discord.Interaction, user: discord.Member):
    """Hapus tickets untuk user tertentu"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Get user's tickets
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Delete ticket items first
        cursor.execute("""
            DELETE FROM ticket_items 
            WHERE ticket_id IN (
                SELECT id FROM tickets WHERE guild_id = ? AND user_id = ?
            )
        """, (str(interaction.guild.id), str(user.id)))
        
        # Delete tickets
        cursor.execute("""
            DELETE FROM tickets WHERE guild_id = ? AND user_id = ?
        """, (str(interaction.guild.id), str(user.id)))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        # Log action
        db.log_action(interaction.guild.id, interaction.user.id, "reset_user_tickets", f"Deleted {deleted_count} tickets for user {user.id}")
        
        await interaction.followup.send(
            f"✅ Berhasil menghapus **{deleted_count}** ticket(s) untuk {user.mention}!",
            ephemeral=True
        )
    
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


@client.tree.command(
    name="reset-all-tickets",
    description="[OWNER] Hapus SEMUA tickets dari semua user di server ini."
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def reset_all_tickets(interaction: discord.Interaction):
    """Hapus semua tickets di server dengan konfirmasi"""
    
    # Hitung total tickets
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM tickets WHERE guild_id = ?
    """, (str(interaction.guild.id),))
    total_tickets = cursor.fetchone()[0]
    conn.close()
    
    if total_tickets == 0:
        await interaction.response.send_message("ℹ️ Tidak ada ticket yang perlu dihapus.", ephemeral=True)
        return
    
    # Buat konfirmasi button
    class ConfirmResetAllView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.value = None
        
        @discord.ui.button(label="✅ Ya, Hapus Semua", style=discord.ButtonStyle.danger)
        async def confirm(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            await interaction_btn.response.defer()
            self.value = True
            self.stop()
        
        @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            await interaction_btn.response.defer()
            self.value = False
            self.stop()
    
    view = ConfirmResetAllView()
    await interaction.response.send_message(
        f"⚠️ **PERINGATAN**\n"
        f"Anda akan menghapus **{total_tickets}** ticket(s) dari SEMUA user di server ini!\n\n"
        f"Apakah Anda yakin?",
        view=view,
        ephemeral=True
    )
    
    await view.wait()
    
    if view.value is None:
        await interaction.followup.send("⏱️ Waktu konfirmasi habis. Reset dibatalkan.", ephemeral=True)
        return
    
    if not view.value:
        await interaction.followup.send("❌ Reset tickets dibatalkan.", ephemeral=True)
        return
    
    # Proses penghapusan
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Delete ticket items first
        cursor.execute("""
            DELETE FROM ticket_items 
            WHERE ticket_id IN (
                SELECT id FROM tickets WHERE guild_id = ?
            )
        """, (str(interaction.guild.id),))
        
        # Delete all tickets
        cursor.execute("""
            DELETE FROM tickets WHERE guild_id = ?
        """, (str(interaction.guild.id),))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        # Log action
        db.log_action(interaction.guild.id, interaction.user.id, "reset_all_tickets", f"Deleted {deleted_count} tickets from all users")
        
        await interaction.followup.send(
            f"✅ **Berhasil menghapus {deleted_count} ticket(s) dari semua user!**\n"
            f"Database telah direset.",
            ephemeral=True
        )
    
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


@client.tree.command(
    name="rollback_backup",
    description="[OWNER] Restore data dari backup terakhir atau dari file backup yang dipilih."
)
@app_commands.describe(
    filename='Nama file backup di folder data/backups (opsional). Jika kosong, gunakan backup terbaru.'
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def rollback_backup(interaction: discord.Interaction, filename: Optional[str] = None):
    await interaction.response.defer(ephemeral=True)

    backup_dir = os.path.join(DATA_DIR, 'backups')
    if not os.path.exists(backup_dir):
        await interaction.response.send_message("❌ Tidak ada folder backup.", ephemeral=True)
        return

    # Pilih file
    if filename:
        backup_file = os.path.join(backup_dir, filename)
        if not os.path.exists(backup_file):
            await interaction.response.send_message(f"❌ File backup `{filename}` tidak ditemukan.", ephemeral=True)
            return
    else:
        # Pilih file terakhir berdasarkan mtime
        files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir) if f.lower().endswith('.json')]
        if not files:
            await interaction.response.send_message("❌ Tidak ditemukan file backup.", ephemeral=True)
            return
        backup_file = max(files, key=os.path.getmtime)

    # Buat backup dari current data sebelum restore (safety)
    try:
        current_stats = db.get_all_user_stats(interaction.guild.id)
        current_data = {
            stat['user_id']: {
                'deals_completed': stat['deals_completed'],
                'total_idr_value': stat['total_idr_value']
            }
            for stat in current_stats
        }
        ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        prebackup_file = os.path.join(backup_dir, f'user_data_pre_restore_{ts}.json')
        with open(prebackup_file, 'w', encoding='utf-8') as pb:
            json.dump(current_data, pb, ensure_ascii=False, indent=2)
    except Exception:
        prebackup_file = None

    # Load selected backup dan restore ke database
    try:
        with open(backup_file, 'r', encoding='utf-8') as bf:
            data = json.load(bf)
        
        # Reset semua stats dulu
        db.reset_all_stats(interaction.guild.id)
        
        # Import dari backup
        conn = db.get_connection()
        cursor = conn.cursor()
        for user_id, stats in data.items():
            deals = stats.get('deals_completed', 0)
            idr_value = stats.get('total_idr_value', 0)
            cursor.execute("""
                INSERT OR REPLACE INTO user_stats (guild_id, user_id, deals_completed, total_idr_value, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (str(interaction.guild.id), user_id, deals, idr_value))
        conn.commit()
        conn.close()
        
        # Log action
        db.log_action(interaction.guild.id, interaction.user.id, "rollback_backup", f"File: {os.path.basename(backup_file)}")
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Gagal melakukan restore: {e}", ephemeral=True)
        return

    resp = f"✅ Restore berhasil dari `{os.path.basename(backup_file)}`."
    if prebackup_file:
        resp += f" Backup sebelum restore disimpan: `{os.path.basename(prebackup_file)}`."
    await interaction.response.send_message(resp, ephemeral=False)


# --- Slash Command: /history ---
@client.tree.command(
    name="list_backups",
    description="[OWNER] Tampilkan daftar file backup yang tersedia."
)
@app_commands.describe(
    limit='Jumlah item yang ditampilkan (default 10, maksimal 50)'
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def list_backups(interaction: discord.Interaction, limit: Optional[int] = 10):
    await interaction.response.defer(ephemeral=True)

    backup_dir = os.path.join(DATA_DIR, 'backups')
    if not os.path.exists(backup_dir):
        await interaction.response.send_message("❌ Tidak ada folder backup.", ephemeral=True)
        return

    files = [f for f in os.listdir(backup_dir) if f.lower().endswith('.json')]
    if not files:
        await interaction.response.send_message("❌ Tidak ditemukan file backup.", ephemeral=True)
        return

    # sort by mtime desc
    files_full = [os.path.join(backup_dir, f) for f in files]
    files_full.sort(key=os.path.getmtime, reverse=True)

    # Pagination UI
    class BackupListView(discord.ui.View):
        def __init__(self, files: list, page: int = 0, items_per_page: int = 5):
            super().__init__(timeout=180)
            self.files = files
            self.page = page
            self.items_per_page = items_per_page
            self.max_pages = (len(files) - 1) // items_per_page + 1
            self.update_buttons()
        
        def update_buttons(self):
            self.previous_button.disabled = (self.page == 0)
            self.next_button.disabled = (self.page >= self.max_pages - 1)
        
        def get_embed(self):
            start = self.page * self.items_per_page
            end = start + self.items_per_page
            page_files = self.files[start:end]
            
            embed = discord.Embed(
                title=f"📦 Daftar Backup (Page {self.page + 1}/{self.max_pages})",
                color=discord.Color.blue()
            )
            
            for idx, path in enumerate(page_files, start=start + 1):
                fname = os.path.basename(path)
                mtime = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
                size = os.path.getsize(path)
                embed.add_field(
                    name=f"{idx}. {fname}",
                    value=f"📅 {mtime} | 💾 {size} bytes",
                    inline=False
                )
            
            embed.set_footer(text=f"Total: {len(self.files)} backup files")
            return embed
        
        @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.secondary)
        async def previous_button(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            if self.page > 0:
                self.page -= 1
                self.update_buttons()
                await interaction_btn.response.edit_message(embed=self.get_embed(), view=self)
        
        @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
        async def next_button(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
            if self.page < self.max_pages - 1:
                self.page += 1
                self.update_buttons()
                await interaction_btn.response.edit_message(embed=self.get_embed(), view=self)
    
    view = BackupListView(files_full)
    await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)


# --- Slash Command: /stats ---
@client.tree.command(
    name="stats", 
    description="Menampilkan statistik Total Transaksi dan Total Spend user." 
)
@app_commands.describe(
    user='Pilih pengguna untuk dilihat statistiknya (default: diri sendiri)'
)
async def stats_command(interaction: discord.Interaction, user: Optional[discord.Member]):
    # Check cooldown untuk #cmd-bot
    is_cooldown, remaining = check_cmd_bot_cooldown(interaction)
    if is_cooldown:
        await interaction.response.send_message(
            f"⏰ **Cooldown Active**\n\nAnda bisa menggunakan command ini lagi dalam **{remaining} detik** di channel #cmd-bot.\n\n"
            f"*Cooldown ini untuk mencegah spam. Admin/Owner tidak terkena cooldown.*",
            ephemeral=True
        )
        return
    
    target_user = user if user is not None else interaction.user
    
    # Ambil stats dari database
    stats = db.get_user_stats(interaction.guild.id, target_user.id)
    if not stats:
        # User belum ada data, buat entry baru dengan nilai 0
        db.update_user_stats(interaction.guild.id, target_user.id, 0)
        stats = {'deals_completed': 0, 'total_idr_value': 0}

    deals = stats.get('deals_completed', 0)
    idr_value = stats.get('total_idr_value', 0)
    
    # Hitung USD (kurs ~15.000 IDR/USD)
    usd_value = idr_value / 15000

    # Buat embed dengan design elegant
    try:
        avatar_url = target_user.display_avatar.url
    except Exception:
        avatar_url = None

    # Elegant cyan gradient
    embed = discord.Embed(
        title=f"👤 {target_user.display_name}",
        description="Statistik Transaksi",
        color=0x00CED1  # Dark turquoise
    )
    if avatar_url:
        embed.set_thumbnail(url=avatar_url)

    # Field dengan design minimalis - 1 kolom vertikal
    embed.add_field(
        name="📊 Total Transaksi", 
        value=f"**{deals}** deals", 
        inline=False
    )
    embed.add_field(
        name="💰 Total Belanja", 
        value=f"**{format_idr(idr_value)}**\n(≈ ${usd_value:,.2f} USD)", 
        inline=False
    )

    embed.set_footer(
        text="💡 Tip: Jangan lupa vouch setelah transaksi!", 
        icon_url=interaction.guild.icon.url if interaction.guild.icon else None
    )

    await interaction.response.send_message(embed=embed, ephemeral=False)
# --- Slash Command: /weekly-leaderboard ---
@client.tree.command(
    name="weekly-leaderboard",
    description="[OWNER] 🏆 Weekly Leaderboard - Reset Ranking Setiap Senin"
)
@app_commands.describe(
    page='Halaman leaderboard (default: 1)',
    per_page='Jumlah user per halaman (default: 10, max: 20)'
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def weekly_leaderboard_command(interaction: discord.Interaction, page: Optional[int] = 1, per_page: Optional[int] = 10):
    await interaction.response.defer()
    
    try:
        # Validasi
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 20:
            per_page = 10
        
        # Ambil WEEKLY leaderboard - TOP 10
        weekly_stats = db.get_weekly_leaderboard(interaction.guild.id, limit=10)
        
        if not weekly_stats:
            await interaction.followup.send("❌ Belum ada data transaksi minggu ini.", ephemeral=True)
            return

        # Ambil member info dengan TIMEOUT protection
        guild = interaction.guild
        stats_list = []
        
        for stat in weekly_stats:
            try:
                # Add timeout untuk fetch_member (max 3 detik per user)
                member = await asyncio.wait_for(
                    guild.fetch_member(int(stat['user_id'])),
                    timeout=3.0
                )
                stats_list.append((
                    member.display_name,
                    stat['deals_count'],
                    stat['weekly_spend'],
                    member
                ))
            except asyncio.TimeoutError:
                # Timeout saat fetch member
                stats_list.append((
                    f"User {stat['user_id']}",
                    stat['deals_count'],
                    stat['weekly_spend'],
                    None
                ))
            except Exception:
                # User mungkin sudah keluar dari server
                stats_list.append((
                    f"User {stat['user_id']}",
                    stat['deals_count'],
                    stat['weekly_spend'],
                    None
                    ))

        if not stats_list:
            await interaction.followup.send("❌ Belum ada user di leaderboard.", ephemeral=True)
            return
        
        # Pagination
        total_users = len(stats_list)
        total_pages = (total_users - 1) // per_page + 1
        if page > total_pages:
            page = total_pages
        
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_users)
        page_stats = stats_list[start_idx:end_idx]
        
        # Import datetime untuk week calculation
        from datetime import datetime as dt, timedelta
        
        # Buat embed dengan tema SULTAN elegant & modern
        embed = discord.Embed(
            title="",
            description="",
            color=0xFFD700,  # Gold color
            timestamp=dt.now()
        )
        
        # Header elegant dengan crown
        embed.set_author(
            name="👑 Weekly Leaderboard — Top Sultan",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        # Thumbnail server icon
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        
        # Ranking icons - attractive for top 3, uniform for 4-10
        ranking_emoji = {
            1: "👑",  # Crown for #1
            2: "🌟",  # Star for #2
            3: "💎"   # Diamond for #3
        }
        
        leaderboard_text = []
        for idx, (name, deals, total_spend, member) in enumerate(page_stats, start_idx + 1):
            # Top 3 get special icons, 4-10 get uniform numbering
            if idx <= 3:
                rank_emoji = ranking_emoji[idx]
            else:
                rank_emoji = f"▫️ `#{idx}`"
            
            # Format clean dengan separator
            leaderboard_text.append(
                f"{rank_emoji} **{name}** `Top {idx}`\n"
                f"   **{deals}** transaksi • 💵 {format_idr(total_spend)}"
            )
    
        # Description dengan layout minimalis elegant
        embed.description = (
            f"🏆 **Top {total_users} Sultan (Minggu Ini)**\n\n" +
            "\n\n".join(leaderboard_text)
        )
        
        # Get week info
        week_start = db.get_current_week_start()
        week_start_dt = dt.strptime(week_start, '%Y-%m-%d')
        next_monday = week_start_dt + timedelta(days=7)
        days_until_reset = (next_monday - dt.now()).days
        
        # Footer dengan info weekly
        footer_text = f"📊 Weekly Stats • Reset dalam {days_until_reset} hari • Page {page}/{total_pages}"
        
        embed.set_footer(text=footer_text, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # ALWAYS send embed to user who requested
        await interaction.followup.send(embed=embed, ephemeral=False)
        
        # ALSO post to #lb-rich-weekly if it exists
        lb_weekly_channel = discord.utils.get(interaction.guild.text_channels, name="lb-rich-weekly")
        
        if lb_weekly_channel:
            try:
                await lb_weekly_channel.send(embed=embed)
                print(f"✅ Weekly leaderboard also posted to #lb-rich-weekly")
            except Exception as e:
                print(f"⚠️ Failed to post to #lb-rich-weekly: {e}")
    
    except Exception as e:
        # Global error handler untuk /weekly-leaderboard
        print(f"❌ Error in /weekly-leaderboard: {e}")
        import traceback
        traceback.print_exc()
        try:
            await interaction.followup.send(
                f"❌ Terjadi error saat generate leaderboard:\n```{str(e)[:200]}```",
                ephemeral=True
            )
        except:
            pass  # Interaction mungkin sudah expired


# --- Slash Command: /allstats (All-Time Leaderboard) ---
@client.tree.command(
    name="allstats",
    description="[OWNER] 🏆 All-Time Leaderboard - Total statistik sepanjang waktu"
)
@app_commands.describe(
    page='Halaman leaderboard (default: 1)',
    per_page='Jumlah user per halaman (default: 10, max: 20)'
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def allstats_command(interaction: discord.Interaction, page: Optional[int] = 1, per_page: Optional[int] = 10):
    await interaction.response.defer()
    
    try:
        # Validasi
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 20:
            per_page = 10
        
        # Ambil ALL-TIME leaderboard
        all_stats = db.get_leaderboard(interaction.guild.id, limit=50)
        
        if not all_stats:
            await interaction.followup.send("❌ Belum ada data transaksi di server ini.", ephemeral=True)
            return

        # Ambil member info dengan TIMEOUT protection
        guild = interaction.guild
        stats_list = []
        
        for stat in all_stats:
            try:
                # Add timeout untuk fetch_member (max 3 detik per user)
                member = await asyncio.wait_for(
                    guild.fetch_member(int(stat['user_id'])),
                    timeout=3.0
                )
                stats_list.append((
                    member.display_name,
                    stat['deals_completed'],
                    stat['total_idr_value'],
                    member
                ))
            except asyncio.TimeoutError:
                # Timeout saat fetch member
                stats_list.append((
                    f"User {stat['user_id']}",
                    stat['deals_completed'],
                    stat['total_idr_value'],
                    None
                ))
            except Exception:
                # User mungkin sudah keluar dari server
                stats_list.append((
                    f"User {stat['user_id']}",
                    stat['deals_completed'],
                    stat['total_idr_value'],
                    None
                ))

        if not stats_list:
            await interaction.followup.send("❌ Belum ada user di leaderboard.", ephemeral=True)
            return
        
        # Pagination
        total_users = len(stats_list)
        total_pages = (total_users - 1) // per_page + 1
        if page > total_pages:
            page = total_pages
        
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_users)
        page_stats = stats_list[start_idx:end_idx]
        
        # Import datetime
        from datetime import datetime as dt
        
        # Buat embed dengan tema SULTAN elegant & modern
        embed = discord.Embed(
            title="",
            description="",
            color=0xFFD700,  # Gold color
            timestamp=dt.now()
        )
        
        # Header elegant dengan crown
        embed.set_author(
            name="👑 All-Time Leaderboard — Top Sultan",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        # Thumbnail server icon
        if interaction.guild.icon:
            embed.set_thumbnail(url=interaction.guild.icon.url)
        
        # Ranking icons
        ranking_emoji = {
            1: "👑",  # Crown for #1
            2: "🌟",  # Star for #2
            3: "💎"   # Diamond for #3
        }
        
        leaderboard_text = []
        for idx, (name, deals, total_spend, member) in enumerate(page_stats, start_idx + 1):
            # Top 3 get special icons
            if idx <= 3:
                rank_emoji = ranking_emoji[idx]
            else:
                rank_emoji = f"▫️ `#{idx}`"
            
            # Format clean
            leaderboard_text.append(
                f"{rank_emoji} **{name}**\n"
                f"   **{deals}** transaksi • 💵 {format_idr(total_spend)}"
            )
    
        # Description
        embed.description = (
            f"🏆 **Top {total_users} Sultan (All-Time)**\n\n" +
            "\n\n".join(leaderboard_text)
        )
        
        # Footer
        footer_text = f"📊 All-Time Stats • Page {page}/{total_pages}"
        embed.set_footer(text=footer_text, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # Send to user
        await interaction.followup.send(embed=embed, ephemeral=False)
    
    except Exception as e:
        print(f"❌ Error in /allstats: {e}")
        import traceback
        traceback.print_exc()
        try:
            await interaction.followup.send(
                f"❌ Terjadi error saat generate leaderboard:\n```{str(e)[:200]}```",
                ephemeral=True
            )
        except:
            pass


# --- Slash Command: /add ---
@client.tree.command(
    name="add",
    description="Tambahkan item ke ticket Anda (gunakan di ticket channel)."
)
@app_commands.describe(
    item='Pilih item yang ingin dibeli'
)
async def add_item(interaction: discord.Interaction, item: str):
    await interaction.response.defer()
    
    ticket = db.get_ticket_by_channel(interaction.channel.id)
    
    if not ticket:
        await interaction.followup.send("❌ Command ini hanya bisa digunakan di ticket channel.", ephemeral=True)
        return
    
    if ticket['status'] != 'open':
        await interaction.followup.send("❌ Ticket ini sudah ditutup.", ephemeral=True)
        return
    
    if int(ticket['user_id']) != interaction.user.id:
        if not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ Hanya owner ticket yang bisa menambahkan item.", ephemeral=True)
            return
    
    # Get item details from database
    item_data = db.get_item_price(interaction.guild.id, item)
    
    if not item_data:
        await interaction.followup.send("❌ Item tidak ditemukan.", ephemeral=True)
        return
    
    item_name = item_data['name']
    unit_price = item_data['price_idr']
    robux = item_data['robux']
    
    db.add_item_to_ticket(
        ticket_id=ticket['id'],
        item_name=item_name,
        amount=unit_price
    )
    
    confirm_embed = discord.Embed(
        title="✨ Item Berhasil Ditambahkan",
        description="Item telah ditambahkan ke dalam order Anda.",
        color=0x9B59B6,  # Elegant purple
        timestamp=datetime.now()
    )
    
    confirm_embed.add_field(name="🛍️ Item", value=f"`{item_name}`", inline=True)
    confirm_embed.add_field(name="💎 Robux", value=f"`{robux} R$`", inline=True)
    confirm_embed.add_field(name="💳 Harga", value=format_idr(unit_price), inline=True)
    
    items = db.get_ticket_items(ticket['id'])
    grand_total = sum(i['amount'] for i in items)
    
    items_list = []
    for i in items:
        items_list.append(f"`{i['item_name']}` — {format_idr(i['amount'])}")
    
    confirm_embed.add_field(
        name="📦 Ringkasan Order",
        value="\n".join(items_list),
        inline=False
    )
    
    confirm_embed.add_field(
        name="💰 Total Pembayaran",
        value=f"**{format_idr(grand_total)}**",
        inline=False
    )
    
    confirm_embed.set_footer(text="💡 Tip: Upload screenshot bukti transfer langsung ke channel ini", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    await interaction.followup.send(embed=confirm_embed)

# Dynamic autocomplete for /add command
@add_item.autocomplete('item')
async def add_item_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete untuk item choices berdasarkan database"""
    items = db.get_all_items(interaction.guild.id)
    
    # Filter berdasarkan input user
    if current:
        items = [i for i in items if current.lower() in i['name'].lower()]
    
    # Return max 25 choices (Discord limit)
    return [
        app_commands.Choice(
            name=f"{item['name']} ({item['robux']} R$ • {format_idr(item['price_idr'])})",
            value=item['code']
        )
        for item in items[:25]
    ]





# --- Slash Command: /approve-ticket ---
@client.tree.command(
    name="approve-ticket",
    description="[ADMIN] Approve transaksi di ticket ini dan close ticket."
)
@app_commands.default_permissions(administrator=True)
async def approve_ticket(interaction: discord.Interaction):
    try:
        ticket = db.get_ticket_by_channel(interaction.channel.id)
        
        if not ticket:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di ticket channel.", ephemeral=True)
            return
        
        if ticket['status'] != 'open':
            await interaction.response.send_message("❌ Ticket ini sudah ditutup.", ephemeral=True)
            return
        
        items = db.get_ticket_items(ticket['id'])
        
        if not items:
            await interaction.response.send_message("❌ Tidak ada item di ticket ini.", ephemeral=True)
            return
        
        grand_total = sum(i['amount'] for i in items)
        
        # ===== CHECKLIST VALIDASI ADMIN =====
        class ValidationChecklist(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
                self.checks = {
                    'account': False,
                    'timestamp': False,
                    'amount': False,
                    'screenshot': False
                }
                self.confirmed = False
            
            def update_all_buttons(self):
                """Helper to update all button states"""
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        if item.custom_id == "check_account":
                            item.label = "☑ Nomor Rekening Cocok" if self.checks['account'] else "☐ Nomor Rekening Cocok"
                            item.style = discord.ButtonStyle.success if self.checks['account'] else discord.ButtonStyle.secondary
                        elif item.custom_id == "check_time":
                            item.label = "☑ Timestamp Transfer Wajar" if self.checks['timestamp'] else "☐ Timestamp Transfer Wajar"
                            item.style = discord.ButtonStyle.success if self.checks['timestamp'] else discord.ButtonStyle.secondary
                        elif item.custom_id == "check_amount":
                            item.label = "☑ Nominal Sesuai" if self.checks['amount'] else "☐ Nominal Sesuai"
                            item.style = discord.ButtonStyle.success if self.checks['amount'] else discord.ButtonStyle.secondary
                        elif item.custom_id == "check_ss":
                            item.label = "☑ Screenshot Asli (Tidak Edit)" if self.checks['screenshot'] else "☐ Screenshot Asli (Tidak Edit)"
                            item.style = discord.ButtonStyle.success if self.checks['screenshot'] else discord.ButtonStyle.secondary
            
            @discord.ui.button(label="☐ Nomor Rekening Cocok", style=discord.ButtonStyle.secondary, custom_id="check_account")
            async def check_account(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                self.checks['account'] = not self.checks['account']
                button.label = "☑ Nomor Rekening Cocok" if self.checks['account'] else "☐ Nomor Rekening Cocok"
                button.style = discord.ButtonStyle.success if self.checks['account'] else discord.ButtonStyle.secondary
                await interaction_btn.response.edit_message(view=self)
            
            @discord.ui.button(label="☐ Timestamp Transfer Wajar", style=discord.ButtonStyle.secondary, custom_id="check_time")
            async def check_timestamp(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                self.checks['timestamp'] = not self.checks['timestamp']
                button.label = "☑ Timestamp Transfer Wajar" if self.checks['timestamp'] else "☐ Timestamp Transfer Wajar"
                button.style = discord.ButtonStyle.success if self.checks['timestamp'] else discord.ButtonStyle.secondary
                await interaction_btn.response.edit_message(view=self)
            
            @discord.ui.button(label="☐ Nominal Sesuai", style=discord.ButtonStyle.secondary, custom_id="check_amount")
            async def check_amount(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                self.checks['amount'] = not self.checks['amount']
                button.label = "☑ Nominal Sesuai" if self.checks['amount'] else "☐ Nominal Sesuai"
                button.style = discord.ButtonStyle.success if self.checks['amount'] else discord.ButtonStyle.secondary
                await interaction_btn.response.edit_message(view=self)
            
            @discord.ui.button(label="☐ Screenshot Asli (Tidak Edit)", style=discord.ButtonStyle.secondary, custom_id="check_ss")
            async def check_screenshot(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                self.checks['screenshot'] = not self.checks['screenshot']
                button.label = "☑ Screenshot Asli (Tidak Edit)" if self.checks['screenshot'] else "☐ Screenshot Asli (Tidak Edit)"
                button.style = discord.ButtonStyle.success if self.checks['screenshot'] else discord.ButtonStyle.secondary
                await interaction_btn.response.edit_message(view=self)
            
            @discord.ui.button(label="⚡ CEK SEMUA", style=discord.ButtonStyle.primary, custom_id="check_all", row=1)
            async def check_all(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                # Toggle: if all checked, uncheck all. Otherwise, check all
                all_checked = all(self.checks.values())
                new_state = not all_checked
                
                for key in self.checks:
                    self.checks[key] = new_state
                
                self.update_all_buttons()
                await interaction_btn.response.edit_message(view=self)
            
            @discord.ui.button(label="✅ APPROVE SEKARANG", style=discord.ButtonStyle.danger, custom_id="confirm_approve", row=1)
            async def confirm_approve(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                # Check if all validations are checked
                if not all(self.checks.values()):
                    unchecked = [k for k, v in self.checks.items() if not v]
                    await interaction_btn.response.send_message(
                        f"⚠️ **Checklist belum lengkap!**\n\n"
                        f"Belum divalidasi: {', '.join(unchecked)}\n\n"
                        f"Pastikan semua checklist sudah ✅ sebelum approve.",
                        ephemeral=True
                    )
                    return
                
                self.confirmed = True
                await interaction_btn.response.defer()
                self.stop()
            
            @discord.ui.button(label="❌ Batal", style=discord.ButtonStyle.secondary, custom_id="cancel_approve", row=1)
            async def cancel_approve(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                self.confirmed = False
                await interaction_btn.response.defer()
                self.stop()
        
        # Show validation checklist
        checklist_embed = discord.Embed(
            title="🔐 Validasi Bukti Transfer",
            description=(
                f"**Admin:** {interaction.user.mention}\n"
                f"**Ticket:** #{ticket['ticket_number']:04d}\n"
                f"**Total:** {format_idr(grand_total)}\n\n"
                f"⚠️ **WAJIB CEK SEMUA** sebelum approve:\n"
                f"Klik setiap item untuk tandai sudah dicek ✅"
            ),
            color=0xE74C3C
        )
        checklist_embed.set_footer(text="⏱️ Timeout: 2 menit • Anti-Fraud System")
        
        view = ValidationChecklist()
        await interaction.response.send_message(embed=checklist_embed, view=view, ephemeral=True)
        
        await view.wait()
        
        if not view.confirmed:
            await interaction.followup.send("❌ Approval dibatalkan.", ephemeral=True)
            return
        
        # Proceed with approval
        await interaction.followup.send("⏳ Memproses approval...", ephemeral=True)
        
        # Update user stats untuk setiap item
        for item in items:
            db.update_user_stats(ticket['guild_id'], int(ticket['user_id']), item['amount'])
            db.add_transaction(
                guild_id=int(ticket['guild_id']),
                user_id=int(ticket['user_id']),
                amount=item['amount'],
                category="ticket_order",
                notes=f"{item['item_name']} - {format_idr(item['amount'])} (Ticket #{ticket['ticket_number']:04d})",
                recorded_by=interaction.user.id
            )
        
        # Check achievements
        new_achievements = db.check_and_unlock_achievement(int(ticket['guild_id']), int(ticket['user_id']))
        
        # Close ticket with approval tracking
        db.close_ticket(ticket['id'], interaction.user.id, approved_by=interaction.user.id)
        
        # Get buyer info
        buyer = interaction.guild.get_member(int(ticket['user_id']))
        vouch_channel = discord.utils.get(interaction.guild.text_channels, name="vouch")
        
        # === SINGLE ELEGANT EMBED ===
        success_embed = discord.Embed(
            title="✨ Transaksi Berhasil",
            description=f"{buyer.mention if buyer else 'Customer'}\n\nPembayaran diverifikasi. Terima kasih atas kepercayaan Anda!",
            color=0x2ECC71,
            timestamp=datetime.now()
        )
        
        success_embed.add_field(
            name="💰 Total",
            value=f"**Rp{grand_total:,}**",
            inline=True
        )
        
        success_embed.add_field(
            name="🎫 Ticket",
            value=f"`#{ticket['ticket_number']:04d}`",
            inline=True
        )
        
        # Achievement badge if unlocked
        if new_achievements:
            ach_names = {
                'deals_10': '🎯 10 Deals',
                'deals_50': '🔥 50 Deals',
                'deals_100': '⭐ 100 Deals',
                'deals_500': '💎 500 Deals',
                'value_1m': '💰 Rp1M',
                'value_5m': '💸 Rp5M',
                'value_10m': '🏆 Rp10M',
                'value_50m': '👑 Rp50M',
            }
            ach_list = []
            for achievement in new_achievements:
                if isinstance(achievement, dict):
                    ach_type = achievement.get('achievement_type', '')
                    ach_list.append(ach_names.get(ach_type, ach_type))
                else:
                    ach_list.append(ach_names.get(achievement, achievement))
            
            success_embed.add_field(
                name="🎉 Achievement",
                value=" • ".join(ach_list),
                inline=False
            )
        
        # Vouch reminder
        if vouch_channel:
            success_embed.add_field(
                name="💌 Testimoni",
                value=f"Share pengalaman kamu di {vouch_channel.mention}",
                inline=False
            )
        
        success_embed.set_footer(
            text="Channel ditutup dalam 60 detik",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        await interaction.followup.send(embed=success_embed)
        
        # Auto-role CUST untuk buyer yang sudah transaksi
        if buyer:
            cust_role = discord.utils.get(interaction.guild.roles, name="CUST")
            guest_role = discord.utils.get(interaction.guild.roles, name="Guest")
            
            if cust_role and cust_role not in buyer.roles:
                try:
                    await buyer.add_roles(cust_role, reason=f"Completed transaction - Ticket #{ticket['ticket_number']:04d}")
                    print(f"✅ Auto-role 'CUST' diberikan ke {buyer.name}")
                    
                    # Auto-remove Guest role jika ada
                    if guest_role and guest_role in buyer.roles:
                        await buyer.remove_roles(guest_role, reason="Upgraded to CUST")
                        print(f"🗑️ Role 'Guest' dihapus dari {buyer.name} (upgrade ke CUST)")
                        
                except Exception as e:
                    print(f"⚠️ Gagal memberikan role CUST: {e}")
        
        # Post updated stats ke #cmd-bot (async, non-blocking)
        import asyncio
        asyncio.create_task(post_stats_to_cmd_bot(interaction, ticket, grand_total, new_achievements))
        
        # Trigger update leaderboard (non-blocking)
        asyncio.create_task(trigger_leaderboard_update(interaction.guild))
        
        # Delete channel after 60 seconds
        await asyncio.sleep(60)
        try:
            await interaction.channel.delete(reason=f"Ticket approved by {interaction.user.name}")
        except Exception as e:
            print(f"❌ Error deleting channel: {e}")
    
    except Exception as e:
        print(f"❌ Error in approve_ticket: {e}")
        try:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
        except:
            pass


async def trigger_leaderboard_update(guild: discord.Guild):
    """Helper function untuk trigger update leaderboard setelah transaksi"""
    try:
        lb_data = db.get_leaderboard_message(guild.id)
        
        if not lb_data:
            # Belum ada leaderboard message, skip
            return
        
        try:
            channel = guild.get_channel(lb_data['channel_id'])
            if not channel:
                return
            
            # Hapus message lama
            try:
                old_message = await channel.fetch_message(lb_data['message_id'])
                await old_message.delete()
            except discord.NotFound:
                pass  # Message sudah dihapus
            
            # Generate embed baru
            embed = await client.generate_leaderboard_embed(guild)
            
            # Post message baru
            new_message = await channel.send(embed=embed)
            
            # Update message ID di database
            db.set_leaderboard_message(guild.id, channel.id, new_message.id)
            
            print(f"✅ Leaderboard updated setelah transaksi di {guild.name}")
            
        except Exception as e:
            print(f"❌ Error update leaderboard: {e}")
            
    except Exception as e:
        print(f"❌ Error trigger leaderboard update: {e}")


async def post_stats_to_cmd_bot(interaction, ticket, grand_total, new_achievements):
    """Helper function to post/update stats to #cmd-bot"""
    try:
        cmd_bot_channel = discord.utils.get(interaction.guild.text_channels, name="cmd-bot")
        if not cmd_bot_channel:
            print("⚠️ #cmd-bot channel not found, skipping stats post")
            return
        
        buyer = interaction.guild.get_member(int(ticket['user_id']))
        stats = db.get_user_stats(int(ticket['guild_id']), int(ticket['user_id']))
        
        if not buyer or not stats:
            print("⚠️ Buyer or stats not found")
            return
        
        # Get USD value
        usd_value = stats['total_idr_value'] / 15000
        
        # Format dengan design elegant
        stats_embed = discord.Embed(
            title=f"👤 {buyer.display_name}",
            description="Statistik Transaksi",
            color=0x3498DB  # Elegant blue
        )
        
        # Set thumbnail (avatar buyer)
        try:
            stats_embed.set_thumbnail(url=buyer.display_avatar.url)
        except:
            pass
        
        # Total Transaksi
        stats_embed.add_field(
            name="📊 Total Transaksi",
            value=f"**{stats['deals_completed']}** deals",
            inline=False
        )
        
        # Total Belanja dengan USD
        stats_embed.add_field(
            name="💰 Total Belanja",
            value=f"**{format_idr(stats['total_idr_value'])}**\n(≈ ${usd_value:,.2f} USD)",
            inline=False
        )
        
        # Tip untuk vouch
        stats_embed.add_field(
            name="💡 Tip: Jangan lupa vouch setelah transaksi!",
            value="\u200b",
            inline=False
        )
        
        # Footer dengan info ticket
        stats_embed.set_footer(
            text=f"✅ Ticket #{ticket['ticket_number']:04d} • Approved by {interaction.user.name}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        # Cek apakah sudah ada message sebelumnya
        existing_msg = db.get_user_stats_message(int(ticket['guild_id']), int(ticket['user_id']))
        
        if existing_msg:
            # Update message yang sudah ada
            try:
                channel = interaction.guild.get_channel(existing_msg['channel_id'])
                if channel:
                    message = await channel.fetch_message(existing_msg['message_id'])
                    await message.edit(content=buyer.mention, embed=stats_embed)
                    print(f"✅ Updated stats in #cmd-bot for {buyer.name}")
                    return
            except discord.NotFound:
                # Message sudah dihapus, post baru
                print(f"⚠️ Old stats message not found, posting new one")
            except Exception as e:
                print(f"⚠️ Error updating stats message: {e}")
        
        # Post message baru
        message = await cmd_bot_channel.send(content=buyer.mention, embed=stats_embed)
        
        # Simpan message ID
        db.set_user_stats_message(int(ticket['guild_id']), int(ticket['user_id']), cmd_bot_channel.id, message.id)
        
        print(f"✅ Posted new stats to #cmd-bot for {buyer.name}")
        
    except Exception as e:
        print(f"❌ Error posting stats to #cmd-bot: {e}")


# --- Slash Command: /reject-ticket ---
@client.tree.command(
    name="reject-ticket",
    description="[ADMIN] Reject transaksi di ticket ini."
)
@app_commands.describe(reason='Alasan penolakan')
@app_commands.default_permissions(administrator=True)
async def reject_ticket(interaction: discord.Interaction, reason: str = "Bukti transfer tidak valid"):
    await interaction.response.defer()
    
    ticket = db.get_ticket_by_channel(interaction.channel.id)
    
    if not ticket:
        await interaction.followup.send("❌ Command ini hanya bisa digunakan di ticket channel.", ephemeral=True)
        return
    
    if ticket['status'] != 'open':
        await interaction.followup.send("❌ Ticket ini sudah ditutup.", ephemeral=True)
        return
    
    # Close ticket
    db.close_ticket(ticket['id'], interaction.user.id)
    
    reject_embed = discord.Embed(
        title="❌ Transaksi Ditolak",
        description=f"Pembayaran tidak dapat diverifikasi oleh admin.",
        color=0xE74C3C,  # Elegant red
        timestamp=datetime.now()
    )
    
    reject_embed.add_field(name="📝 Alasan Penolakan", value=reason, inline=False)
    reject_embed.add_field(name="💡 Saran", value="Silakan hubungi admin untuk klarifikasi lebih lanjut.", inline=False)
    reject_embed.set_footer(text="🕒 Channel akan ditutup dalam 30 detik", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
    
    await interaction.channel.send(embed=reject_embed)
    await interaction.followup.send("❌ Rejected! Channel akan dihapus dalam 30 detik.")
    
    import asyncio
    await asyncio.sleep(30)
    try:
        await interaction.channel.delete(reason=f"Ticket rejected by {interaction.user.name}")
    except:
        pass


# --- Slash Command: /close ---
@client.tree.command(
    name="close",
    description="Tutup ticket Anda (buyer atau admin)."
)
async def close_ticket(interaction: discord.Interaction):
    try:
        await interaction.response.defer()
        
        ticket = db.get_ticket_by_channel(interaction.channel.id)
        
        if not ticket:
            await interaction.followup.send("❌ Command ini hanya bisa digunakan di ticket channel.", ephemeral=True)
            return
        
        if ticket['status'] != 'open':
            await interaction.followup.send("❌ Ticket ini sudah ditutup.", ephemeral=True)
            return
        
        # Check permission
        if int(ticket['user_id']) != interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send("❌ Hanya owner ticket atau admin yang bisa close ticket.", ephemeral=True)
            return
        
        db.close_ticket(ticket['id'], interaction.user.id)
        
        close_embed = discord.Embed(
            title="🔒 Ticket Ditutup",
            description=f"Ticket telah ditutup oleh {interaction.user.mention}",
            color=0xE67E22,  # Elegant orange
            timestamp=datetime.now()
        )
        
        close_embed.add_field(name="💬 Catatan", value="Terima kasih telah menggunakan layanan kami.", inline=False)
        close_embed.set_footer(text="🕑 Channel akan dihapus dalam 10 detik", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.followup.send("✅ Ticket ditutup. Channel akan dihapus dalam 10 detik.")
        await interaction.channel.send(embed=close_embed)
        
        # Delete channel after 10 seconds
        import asyncio
        await asyncio.sleep(10)
        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except Exception as e:
            print(f"❌ Error deleting channel: {e}")
    
    except Exception as e:
        print(f"❌ Error in close_ticket: {e}")
        try:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
        except:
            pass


# --- Slash Command: /setup-ticket ---
@client.tree.command(
    name="setup-ticket",
    description="[OWNER] Setup channel open-ticket untuk buyer."
)
@owner_only()
async def setup_ticket_channel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Cek apakah channel sudah ada
    existing_channel = discord.utils.get(interaction.guild.text_channels, name="open-ticket")
    
    if existing_channel:
        await interaction.followup.send(
            f"✅ Channel {existing_channel.mention} sudah ada.\n"
            f"Buyer bisa langsung ketik username game mereka di channel tersebut untuk buka ticket.",
            ephemeral=True
        )
        return
    
    # Buat channel open-ticket
    try:
        # Cari kategori "TICKETS" (case-insensitive)
        tickets_category = None
        for category in interaction.guild.categories:
            if category.name.upper() == "TICKETS":
                tickets_category = category
                break
        
        # Create channel dengan permission @everyone bisa read & send
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=False,
                attach_files=False
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True
            )
        }
        
        channel = await interaction.guild.create_text_channel(
            name="open-ticket",
            overwrites=overwrites,
            category=tickets_category,  # Masukkan ke kategori TICKETS jika ada
            topic="📝 Ketik username game Anda di sini untuk membuka ticket order"
        )
        
        # Kirim instruksi di channel
        # Initialize items if not exists
        items = db.get_all_items(interaction.guild.id)
        if not items:
            db.init_default_items(interaction.guild.id)
            items = db.get_all_items(interaction.guild.id)
        
        rate = db.get_robux_rate(interaction.guild.id)
        
        instruction_embed = discord.Embed(
            title="🎫 Open Ticket - Panduan",
            description=f"Selamat datang! Gift Fish-It Roblox dengan rate **Rp{rate}/Robux**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        instruction_embed.add_field(
            name="📝 Cara Buka Ticket",
            value=(
                "**1.** Klik tombol **Create Ticket** di bawah\n\n"
                "**2.** Input username game Anda (min 3 karakter)\n"
                "**Contoh:** `AbuyyXZ777`\n\n"
                "**3.** Bot akan create private ticket channel\n\n"
                "**4.** Pilih item dari dropdown menu di ticket\n\n"
                "**5.** Masukkan quantity & konfirmasi\n\n"
                "**6.** Upload bukti pembayaran (auto-detect)"
            ),
            inline=False
        )
        
        instruction_embed.add_field(
            name="💳 Pembayaran",
            value="Admin akan berikan **QRIS** di ticket Anda",
            inline=False
        )
        
        instruction_embed.add_field(
            name="⚡ Penting",
            value=(
                "• 1 user hanya bisa punya 1 ticket aktif\n"
                "• Upload bukti transfer ASLI (tidak boleh edit)\n"
                "• Button akan tetap ada meski bot restart\n"
                "• Pilih item langsung dari dropdown menu"
            ),
            inline=False
        )
        
        instruction_embed.set_footer(text="🎮 Fish-It Roblox Gift Service • Trusted Seller")
        
        # Send embed with button
        view = CreateTicketButton()
        message = await channel.send(embed=instruction_embed, view=view)
        
        # Save message ID to database
        db.set_ticket_setup_message(interaction.guild.id, channel.id, message.id, "rate_system")
        
        # Konfirmasi ke admin
        category_info = f" di kategori **{tickets_category.name}**" if tickets_category else ""
        await interaction.followup.send(
            f"✅ Channel {channel.mention} berhasil dibuat{category_info}!\n\n"
            f"**Setup selesai!** Buyer sekarang bisa:\n"
            f"1. Masuk ke {channel.mention}\n"
            f"2. Klik tombol **Create Ticket**\n"
            f"3. Input username game mereka\n"
            f"4. Bot akan auto-create ticket private channel\n\n"
            f"**Note:** Pastikan bot punya permission `Manage Channels` dan `Manage Messages`.\n"
            f"Button akan tetap ada meskipun bot restart (persistent button).",
            ephemeral=True
        )
        
        # Log action
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="setup_ticket_channel",
            details=f"Created #open-ticket channel: {channel.id}"
        )
        
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Bot tidak punya permission untuk membuat channel.\n"
            "Enable `Manage Channels` permission untuk bot role.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /setup-mm ---
@client.tree.command(
    name="setup-mm",
    description="[OWNER] Setup channel untuk middleman ticket system."
)
@owner_only()
async def setup_mm_channel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Cek apakah channel sudah ada
    existing_channel = discord.utils.get(interaction.guild.text_channels, name="create-ticket-mm")
    
    if existing_channel:
        await interaction.followup.send(
            f"✅ Channel {existing_channel.mention} sudah ada.\n"
            f"User bisa langsung klik button untuk create middleman ticket.",
            ephemeral=True
        )
        return
    
    # Buat channel create-ticket-mm
    try:
        # Cari kategori "TICKET MIDDLEMAN" atau buat baru
        mm_category = discord.utils.get(interaction.guild.categories, name="TICKET MIDDLEMAN")
        if not mm_category:
            mm_category = await interaction.guild.create_category(name="TICKET MIDDLEMAN")
        
        # Create channel
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=False,  # User tidak bisa kirim message, hanya klik button
                add_reactions=False,
                attach_files=False
            ),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True
            )
        }
        
        channel = await interaction.guild.create_text_channel(
            name="create-ticket-mm",
            overwrites=overwrites,
            category=mm_category,
            topic="🤝 Klik button untuk membuka middleman ticket"
        )
        
        # Kirim instruksi di channel
        instruction_embed = discord.Embed(
            title="🤝 Middleman Service - Panduan",
            description="Selamat datang di layanan Middleman! Kami memfasilitasi transaksi antara buyer dan seller dengan aman.",
            color=0xFF9900,  # Orange
            timestamp=datetime.now()
        )
        
        instruction_embed.add_field(
            name="📝 Cara Menggunakan Middleman",
            value=(
                "**1.** Klik tombol **Create Middleman Ticket** di bawah\n\n"
                "**2.** Isi form:\n"
                "   • Username Buyer (in-game)\n"
                "   • Username/ID Seller\n"
                "   • Item/Jasa yang ditransaksikan\n"
                "   • Harga yang sudah disepakati\n\n"
                "**3.** Bot akan create private channel untuk transaksi\n\n"
                "**4.** Buyer transfer ke rekening middleman\n\n"
                "**5.** Seller kirim item setelah payment verified\n\n"
                "**6.** Admin release dana ke seller setelah buyer konfirmasi"
            ),
            inline=False
        )
        
        instruction_embed.add_field(
            name="💰 Fee Middleman",
            value=(
                "```\n"
                "< Rp50.000       : GRATIS\n"
                "Rp50.000-500K    : Rp2.000\n"
                "Rp500K-1Juta     : Rp5.000\n"
                "Rp1Juta-5Juta    : Rp7.000\n"
                "Rp5Juta-10Juta   : Rp10.000\n"
                "Rp10Juta+        : Rp15.000\n"
                "```\n"
                "*Fee dapat dibayar oleh buyer, seller, atau split 50:50 (>5M)*"
            ),
            inline=False
        )
        
        instruction_embed.add_field(
            name="💳 Metode Pembayaran",
            value=(
                "**QRIS** - Scan & bayar langsung\n"
                "Admin akan berikan QRIS di ticket Anda"
            ),
            inline=False
        )
        
        instruction_embed.add_field(
            name="✅ Keuntungan Pakai Middleman",
            value=(
                "• 🛡️ **Aman** - Dana ditahan sampai seller kirim item\n"
                "• 🤝 **Terpercaya** - Admin memverifikasi semua transaksi\n"
                "• ⚡ **4-Layer Fraud Detection** - Bukti palsu auto-reject\n"
                "• 💸 **Fee Murah** - Mulai dari GRATIS untuk <50K"
            ),
            inline=False
        )
        
        instruction_embed.add_field(
            name="⚠️ Penting",
            value=(
                "• Upload bukti transfer ASLI (tidak boleh edit/crop)\n"
                "• 1 user hanya bisa punya 1 ticket aktif\n"
                "• Gunakan `/close` untuk membatalkan transaksi\n"
                "• Button akan tetap ada meski bot restart"
            ),
            inline=False
        )
        
        instruction_embed.set_footer(text="Klik tombol di bawah untuk mulai! • Trusted Middleman Service")
        
        # Send embed with button
        view = CreateMiddlemanButton()
        message = await channel.send(embed=instruction_embed, view=view)
        
        # Konfirmasi ke admin
        await interaction.followup.send(
            f"✅ Channel {channel.mention} berhasil dibuat di kategori **{mm_category.name}**!\n\n"
            f"**Setup selesai!** User sekarang bisa:\n"
            f"1. Masuk ke {channel.mention}\n"
            f"2. Klik tombol **Create Middleman Ticket**\n"
            f"3. Isi form transaksi\n"
            f"4. Bot akan auto-create middleman ticket channel\n\n"
            f"**Note:** Pastikan bot punya permission `Manage Channels` dan `Manage Messages`.\n"
            f"Button akan tetap ada meskipun bot restart (persistent button).",
            ephemeral=True
        )
        
        # Log action
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="setup_mm_channel",
            details=f"Created #create-ticket-mm channel: {channel.id}"
        )
        
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Bot tidak punya permission untuk membuat channel.\n"
            "Enable `Manage Channels` permission untuk bot role.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /clear ---
@client.tree.command(
    name="clear",
    description="[OWNER] Hapus semua pesan di channel ini."
)
@app_commands.describe(
    amount='Jumlah pesan yang akan dihapus (default: semua)'
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def clear(interaction: discord.Interaction, amount: int = None):
    """Hapus pesan di channel"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        if amount is None:
            # Hapus semua pesan (batch 100 per request)
            deleted_total = 0
            while True:
                deleted = await interaction.channel.purge(limit=100)
                deleted_total += len(deleted)
                if len(deleted) < 100:
                    break
            
            msg = await interaction.followup.send(
                f"✅ Berhasil menghapus **{deleted_total}** pesan dari {interaction.channel.mention}!",
                ephemeral=True
            )
        else:
            # Hapus sejumlah pesan tertentu
            deleted = await interaction.channel.purge(limit=amount)
            msg = await interaction.followup.send(
                f"✅ Berhasil menghapus **{len(deleted)}** pesan dari {interaction.channel.mention}!",
                ephemeral=True
            )
        
        # Auto-delete pesan ephemeral setelah 3 detik
        await asyncio.sleep(3)
        await msg.delete()
        
        # Log action
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="clear_channel",
            details=f"Cleared {deleted_total if amount is None else len(deleted)} messages in {interaction.channel.name}"
        )
        
    except discord.Forbidden:
        msg = await interaction.followup.send(
            "❌ Bot tidak punya permission untuk menghapus pesan.\n"
            "Enable `Manage Messages` permission untuk bot role.",
            ephemeral=True
        )
        await asyncio.sleep(5)
        await msg.delete()
    except discord.HTTPException as e:
        msg = await interaction.followup.send(
            f"❌ Error: {e}\n"
            "Note: Discord hanya mengizinkan hapus pesan yang lebih baru dari 14 hari.",
            ephemeral=True
        )
        await asyncio.sleep(5)
        await msg.delete()
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /set-admin ---
@client.tree.command(
    name="set-admin",
    description="[OWNER] Tambah role sebagai Admin untuk manage bot."
)
@app_commands.describe(role='Role yang akan dijadikan admin')
@owner_only()
async def set_admin(interaction: discord.Interaction, role: discord.Role):
    """Set admin role untuk bot (Owner only)"""
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild_config = db.get_guild_config(interaction.guild.id) or {}
        admin_roles = guild_config.get('admin_roles', [])
        
        if str(role.id) in admin_roles:
            await interaction.followup.send(
                f"❌ Role {role.mention} sudah menjadi Admin!",
                ephemeral=True
            )
            return
        
        admin_roles.append(str(role.id))
        db.set_guild_config(interaction.guild.id, 'admin_roles', admin_roles)
        
        await interaction.followup.send(
            f"✅ Role {role.mention} berhasil ditambahkan sebagai **Admin Bot**!\n\n"
            f"Admin sekarang bisa:\n"
            f"• Approve/Reject ticket\n"
            f"• Lihat statistik semua user\n"
            f"• Hapus pesan (clear)\n"
            f"• Backup/restore data\n"
            f"• Monitor transaksi",
            ephemeral=True
        )
        
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="set_admin_role",
            details=f"Added admin role: {role.name} ({role.id})"
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /remove-admin ---
@client.tree.command(
    name="remove-admin",
    description="[OWNER] Hapus role Admin dari bot."
)
@app_commands.describe(role='Role yang akan dihapus dari admin')
@owner_only()
async def remove_admin(interaction: discord.Interaction, role: discord.Role):
    """Remove admin role (Owner only)"""
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild_config = db.get_guild_config(interaction.guild.id) or {}
        admin_roles = guild_config.get('admin_roles', [])
        
        if str(role.id) not in admin_roles:
            await interaction.followup.send(
                f"❌ Role {role.mention} bukan Admin!",
                ephemeral=True
            )
            return
        
        admin_roles.remove(str(role.id))
        db.set_guild_config(interaction.guild.id, 'admin_roles', admin_roles)
        
        await interaction.followup.send(
            f"✅ Role {role.mention} berhasil dihapus dari Admin Bot!",
            ephemeral=True
        )
        
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="remove_admin_role",
            details=f"Removed admin role: {role.name} ({role.id})"
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /list-admins ---
@client.tree.command(
    name="list-admins",
    description="[ADMIN] Lihat daftar Admin bot di server ini."
)
@app_commands.default_permissions(administrator=True)
async def list_admins(interaction: discord.Interaction):
    """List all admin roles"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        guild_config = db.get_guild_config(interaction.guild.id) or {}
        admin_roles = guild_config.get('admin_roles', [])
        
        embed = discord.Embed(
            title="👥 Admin Management",
            description=f"**Owner:** <@{interaction.guild.owner_id}>",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if admin_roles:
            role_mentions = []
            for role_id in admin_roles:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    role_mentions.append(f"• {role.mention}")
            
            embed.add_field(
                name="🛡️ Admin Roles",
                value="\n".join(role_mentions) if role_mentions else "Tidak ada",
                inline=False
            )
        else:
            embed.add_field(
                name="🛡️ Admin Roles",
                value="Belum ada role admin. Gunakan `/set-admin` untuk menambah.",
                inline=False
            )
        
        # Admin Permissions
        embed.add_field(
            name="✅ Admin Dapat:",
            value=(
                "• `/approve-ticket` - Approve transaksi\n"
                "• `/reject-ticket` - Reject transaksi\n"
                "• `/ticket-stats` - Lihat statistik ticket\n"
                "• `/user-info` - Info detail user\n"
                "• `/audit-log` - Lihat log aktivitas\n"
                "• `/list-admins` - Lihat daftar admin\n"
                "• `/addrole` - Kasih role ke user\n"
                "• `/removerole` - Hapus role dari user"
            ),
            inline=False
        )
        
        # Owner Only Permissions
        embed.add_field(
            name="👑 Owner Only:",
            value=(
                "• `/set-admin` - Tambah admin role\n"
                "• `/remove-admin` - Hapus admin role\n"
                "• `/setup-ticket` - Setup channel ticket\n"
                "• `/reset-tickets` - Reset semua ticket\n"
                "• `/broadcast` - Broadcast message\n"
                "• `/clear` - Hapus banyak pesan\n"
                "• **Full Access** ke semua command"
            ),
            inline=False
        )
        
        embed.set_footer(text="⚠️ Admin role dibatasi untuk keamanan • Hanya Owner full access")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /permissions ---
@client.tree.command(
    name="permissions",
    description="[OWNER] Lihat permission level dan command yang tersedia."
)
@owner_only()
async def permissions(interaction: discord.Interaction):
    """Cek permission level user"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Cek level
        is_owner_user = is_owner(interaction)
        is_admin_user = is_admin_or_owner(interaction)
        
        if is_owner_user:
            level = "👑 **OWNER**"
            color = discord.Color.gold()
        elif is_admin_user:
            level = "🛡️ **ADMIN**"
            color = discord.Color.blue()
        else:
            level = "👤 **USER**"
            color = discord.Color.green()
        
        embed = discord.Embed(
            title=f"🔐 Permission Level: {level}",
            color=color,
            timestamp=datetime.now()
        )
        
        if is_owner_user:
            embed.add_field(
                name="✅ Owner Commands (Full Access):",
                value=(
                    "**Setup & Config:**\n"
                    "• `/set-admin` - Manage admin roles\n"
                    "• `/remove-admin` - Remove admin roles\n"
                    "• `/setup-ticket` - Setup ticket system\n"
                    "• `/reset-tickets` - Reset all tickets\n\n"
                    "**Management:**\n"
                    "• `/broadcast` - Send announcements\n"
                    "• `/clear` - Bulk delete messages\n\n"
                    "**Plus ALL Admin & User commands**"
                ),
                inline=False
            )
        elif is_admin_user:
            embed.add_field(
                name="✅ Admin Commands:",
                value=(
                    "**Ticket Management:**\n"
                    "• `/approve-ticket` - Approve transactions\n"
                    "• `/reject-ticket` - Reject transactions\n\n"
                    "**User Management:**\n"
                    "• `/addrole` - Give role to user\n"
                    "• `/removerole` - Remove role from user\n\n"
                    "**Monitoring:**\n"
                    "• `/ticket-stats` - View ticket statistics\n"
                    "• `/user-info` - View user details\n"
                    "• `/audit-log` - View activity logs\n"
                    "• `/list-admins` - View admin list\n\n"
                    "**Plus ALL User commands**"
                ),
                inline=False
            )
            
            embed.add_field(
                name="❌ Tidak Bisa:",
                value=(
                    "• Setup/Reset system\n"
                    "• Manage admin roles\n"
                    "• Broadcast messages\n"
                    "• Bulk delete messages"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="✅ User Commands:",
                value=(
                    "• `/stats` - View your statistics\n"
                    "• `/leaderboard` - View top spenders\n"
                    "• `/close` - Close your ticket\n"
                    "• `/permissions` - Check your permissions\n"
                    "• **Create tickets** via #open-ticket button"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"User: {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)




# --- Slash Command: /user-info ---
@client.tree.command(
    name="user-info",
    description="[ADMIN] Lihat info detail user tertentu."
)
@app_commands.describe(user='User yang ingin dilihat')
@app_commands.default_permissions(administrator=True)
async def user_info(interaction: discord.Interaction, user: discord.Member):
    """Admin command untuk lihat detail user"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        stats = db.get_user_stats(interaction.guild.id, user.id)
        
        embed = discord.Embed(
            title=f"👤 User Info: {user.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="🆔 User ID",
            value=f"`{user.id}`",
            inline=False
        )
        
        embed.add_field(
            name="📅 Join Date",
            value=f"<t:{int(user.joined_at.timestamp())}:F>",
            inline=False
        )
        
        if stats:
            embed.add_field(
                name="🎫 Total Transaksi",
                value=str(stats['deals_completed']),
                inline=True
            )
            
            embed.add_field(
                name="💰 Total Spend",
                value=format_idr(stats['total_idr_value']),
                inline=True
            )
            
            # Cek achievements
            achievements = db.get_user_achievements(interaction.guild.id, user.id)
            if achievements:
                ach_icons = {
                    'deals_10': '🎯', 'deals_50': '🔥', 'deals_100': '⭐', 'deals_500': '💎',
                    'value_1m': '💰', 'value_5m': '💸', 'value_10m': '🏆', 'value_50m': '👑'
                }
                ach_list = [f"{ach_icons.get(a['achievement_type'], '🏅')} {a['achievement_type']}" 
                           for a in achievements]
                
                embed.add_field(
                    name=f"🏆 Achievements ({len(achievements)})",
                    value="\n".join(ach_list[:5]),
                    inline=False
                )
        else:
            embed.add_field(
                name="📊 Stats",
                value="User belum pernah bertransaksi",
                inline=False
            )
        
        # Cek open tickets
        open_ticket = db.get_open_ticket(interaction.guild.id, user.id)
        if open_ticket:
            channel = interaction.guild.get_channel(int(open_ticket['channel_id']))
            embed.add_field(
                name="🎫 Active Ticket",
                value=f"{channel.mention if channel else 'Channel not found'}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /addrole ---
@client.tree.command(
    name="addrole",
    description="[ADMIN] Berikan role ke user."
)
@app_commands.describe(
    user='User yang akan diberi role',
    role='Role yang akan diberikan'
)
@app_commands.default_permissions(administrator=True)
async def addrole(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    """Berikan role ke user"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Cek apakah user sudah punya role
        if role in user.roles:
            await interaction.followup.send(
                f"❌ {user.mention} sudah memiliki role {role.mention}!",
                ephemeral=True
            )
            return
        
        # Cek apakah bot bisa manage role ini
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.followup.send(
                f"❌ Role {role.mention} lebih tinggi dari role bot. Bot tidak bisa manage role ini!",
                ephemeral=True
            )
            return
        
        # Cek apakah admin bisa manage role ini
        if role.position >= interaction.user.top_role.position and not is_owner(interaction):
            await interaction.followup.send(
                f"❌ Role {role.mention} lebih tinggi dari role kamu!",
                ephemeral=True
            )
            return
        
        # Berikan role
        await user.add_roles(role, reason=f"Added by {interaction.user.name}")
        
        await interaction.followup.send(
            f"✅ Berhasil memberikan role {role.mention} ke {user.mention}!",
            ephemeral=True
        )
        
        # Log action
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="add_role",
            details=f"Added {role.name} to {user.name}"
        )
        
        # Kirim DM ke user (opsional)
        try:
            dm_embed = discord.Embed(
                title="🎉 Role Baru!",
                description=f"Kamu mendapat role **{role.name}** di server **{interaction.guild.name}**!",
                color=role.color,
                timestamp=datetime.now()
            )
            dm_embed.set_footer(text=f"Diberikan oleh {interaction.user.display_name}")
            await user.send(embed=dm_embed)
        except:
            pass  # Ignore jika DM gagal
            
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Bot tidak punya permission untuk manage roles!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /removerole ---
@client.tree.command(
    name="removerole",
    description="[ADMIN] Hapus role dari user."
)
@app_commands.describe(
    user='User yang akan dihapus rolenya',
    role='Role yang akan dihapus'
)
@app_commands.default_permissions(administrator=True)
async def removerole(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    """Hapus role dari user"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Cek apakah user punya role ini
        if role not in user.roles:
            await interaction.followup.send(
                f"❌ {user.mention} tidak memiliki role {role.mention}!",
                ephemeral=True
            )
            return
        
        # Cek apakah bot bisa manage role ini
        if role.position >= interaction.guild.me.top_role.position:
            await interaction.followup.send(
                f"❌ Role {role.mention} lebih tinggi dari role bot. Bot tidak bisa manage role ini!",
                ephemeral=True
            )
            return
        
        # Cek apakah admin bisa manage role ini
        if role.position >= interaction.user.top_role.position and not is_owner(interaction):
            await interaction.followup.send(
                f"❌ Role {role.mention} lebih tinggi dari role kamu!",
                ephemeral=True
            )
            return
        
        # Hapus role
        await user.remove_roles(role, reason=f"Removed by {interaction.user.name}")
        
        await interaction.followup.send(
            f"✅ Berhasil menghapus role {role.mention} dari {user.mention}!",
            ephemeral=True
        )
        
        # Log action
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="remove_role",
            details=f"Removed {role.name} from {user.name}"
        )
            
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Bot tidak punya permission untuk manage roles!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /set-rate ---
@client.tree.command(
    name="set-rate",
    description="[OWNER] Ubah rate Robux (harga per 1 Robux dalam Rupiah)."
)
@app_commands.describe(
    rate="Rate baru per Robux (contoh: 90 untuk Rp90/Robux)"
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def set_rate(interaction: discord.Interaction, rate: int):
    """Set rate Robux dan auto-update semua harga item"""
    await interaction.response.defer(ephemeral=True)
    
    if rate < 10:
        await interaction.followup.send("❌ Rate minimal Rp10 per Robux", ephemeral=True)
        return
    
    if rate > 1000:
        await interaction.followup.send("❌ Rate maksimal Rp1.000 per Robux", ephemeral=True)
        return
    
    # Get old rate
    old_rate = db.get_robux_rate(interaction.guild.id)
    
    # Update rate in database
    db.set_robux_rate(interaction.guild.id, rate)
    
    # Initialize items if not exists
    items = db.get_all_items(interaction.guild.id)
    if not items:
        db.init_default_items(interaction.guild.id)
        items = db.get_all_items(interaction.guild.id)
    
    # Auto-update ticket setup embed
    setup_data = db.get_ticket_setup_message(interaction.guild.id)
    
    if setup_data:
        try:
            channel = interaction.guild.get_channel(setup_data['channel_id'])
            if channel:
                message = await channel.fetch_message(setup_data['message_id'])
                
                # Recreate embed dengan harga baru
                instruction_embed = discord.Embed(
                    title="🎫 Open Ticket - Panduan",
                    description=f"Selamat datang! Gift Fish-It Roblox dengan rate **Rp{rate}/Robux**",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                instruction_embed.add_field(
                    name="📝 Cara Buka Ticket",
                    value=(
                        "**1.** Klik tombol **Create Ticket** di bawah\n\n"
                        "**2.** Input username game Anda (min 3 karakter)\n"
                        "**Contoh:** `AbuyyXZ777`\n\n"
                        "**3.** Bot akan otomatis create private ticket channel untuk Anda\n\n"
                        "**4.** Masuk ke ticket channel dan gunakan `/add` untuk order item\n\n"
                        "**5.** Setelah order selesai, transfer dan `/submit` bukti transfer"
                    ),
                    inline=False
                )
                
                # Build item list from database
                items_text = []
                for item in items:
                    items_text.append(f"**{item['name']}:** {item['robux']} R$ • {format_idr(item['price_idr'])}")
                
                instruction_embed.add_field(
                    name=f"💎 Item & Harga (Rate: Rp{rate}/Robux)",
                    value="\n".join(items_text),
                    inline=False
                )
                
                instruction_embed.add_field(
                    name="💳 Pembayaran",
                    value="Admin akan berikan **QRIS** di ticket Anda",
                    inline=False
                )
                
                instruction_embed.add_field(
                    name="⚡ Penting",
                    value=(
                        "• 1 user hanya bisa punya 1 ticket aktif\n"
                        "• Upload bukti transfer ASLI (tidak boleh edit)\n"
                        "• Button akan tetap ada meski bot restart\n"
                        "• Gunakan `/add` di ticket untuk order"
                    ),
                    inline=False
                )
                
                instruction_embed.set_footer(text="🎮 Fish-It Roblox Gift Service • Trusted Seller")
                
                # Update message
                await message.edit(embed=instruction_embed)
                
                await interaction.followup.send(
                    f"✅ **Rate berhasil diupdate!**\n\n"
                    f"**Rate Lama:** Rp{old_rate}/Robux\n"
                    f"**Rate Baru:** Rp{rate}/Robux\n\n"
                    f"**Perubahan Harga:**\n" +
                    "\n".join([f"• {item['name']}: {format_idr(item['robux'] * old_rate)} → {format_idr(item['price_idr'])}" for item in items[:5]]) +
                    f"\n\n📌 Display di {channel.mention} sudah auto-update!",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.followup.send(
                f"✅ Rate diupdate ke Rp{rate}/Robux\n\n"
                f"⚠️ Gagal update display: {e}\n"
                f"Gunakan `/setup-ticket` ulang untuk refresh display.",
                ephemeral=True
            )
    else:
        await interaction.followup.send(
            f"✅ **Rate berhasil diupdate!**\n\n"
            f"**Rate Lama:** Rp{old_rate}/Robux\n"
            f"**Rate Baru:** Rp{rate}/Robux\n\n"
            f"💡 Gunakan `/setup-ticket` untuk setup channel dengan harga baru.",
            ephemeral=True
        )
    
    # Log action
    db.log_action(
        guild_id=interaction.guild.id,
        user_id=interaction.user.id,
        action="set_rate",
        details=f"Rate updated: Rp{old_rate} → Rp{rate} per Robux"
    )


# --- Slash Command: /add-item ---
@client.tree.command(
    name="add-item",
    description="[OWNER] Tambah item baru ke katalog"
)
@app_commands.describe(
    code="Kode item (contoh: vip_luck, gacha_1x)",
    name="Nama item (contoh: VIP + Luck)",
    robux="Harga dalam Robux (contoh: 445)"
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def add_item_to_catalog(interaction: discord.Interaction, code: str, name: str, robux: int):
    """Tambah item baru ke katalog"""
    await interaction.response.defer(ephemeral=True)
    
    if robux < 1:
        await interaction.followup.send("❌ Harga Robux minimal 1", ephemeral=True)
        return
    
    if robux > 10000:
        await interaction.followup.send("❌ Harga Robux maksimal 10.000", ephemeral=True)
        return
    
    # Check if code already exists
    existing = db.get_item_price(interaction.guild.id, code)
    if existing:
        await interaction.followup.send(f"❌ Item dengan kode `{code}` sudah ada!", ephemeral=True)
        return
    
    # Add item
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO item_prices (guild_id, item_code, item_name, base_robux)
        VALUES (?, ?, ?, ?)
    """, (str(interaction.guild.id), code, name, robux))
    conn.commit()
    conn.close()
    
    # Get price with current rate
    rate = db.get_robux_rate(interaction.guild.id)
    price_idr = robux * rate
    
    # Auto-update setup-ticket embed if exists
    setup_data = db.get_ticket_setup_message(interaction.guild.id)
    
    if setup_data:
        try:
            channel = interaction.guild.get_channel(setup_data['channel_id'])
            if channel:
                message = await channel.fetch_message(setup_data['message_id'])
                
                # Get all items
                items = db.get_all_items(interaction.guild.id)
                
                # Recreate embed
                instruction_embed = discord.Embed(
                    title="🎫 Open Ticket - Panduan",
                    description=f"Selamat datang! Gift Fish-It Roblox dengan rate **Rp{rate}/Robux**",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                instruction_embed.add_field(
                    name="📝 Cara Buka Ticket",
                    value=(
                        "**1.** Klik tombol **Create Ticket** di bawah\n\n"
                        "**2.** Input username game Anda (min 3 karakter)\n"
                        "**Contoh:** `AbuyyXZ777`\n\n"
                        "**3.** Bot akan create private ticket channel\n\n"
                        "**4.** Lihat list item & harga di ticket channel\n\n"
                        "**5.** Gunakan `/add` untuk order item\n\n"
                        "**6.** Upload bukti pembayaran (auto-detect)"
                    ),
                    inline=False
                )
                
                instruction_embed.add_field(
                    name="💳 Pembayaran",
                    value="Admin akan berikan **QRIS** di ticket Anda",
                    inline=False
                )
                
                instruction_embed.add_field(
                    name="⚡ Penting",
                    value=(
                        "• 1 user hanya bisa punya 1 ticket aktif\n"
                        "• Upload bukti transfer ASLI (tidak boleh edit)\n"
                        "• Button akan tetap ada meski bot restart\n"
                        "• Gunakan `/add` di ticket untuk order"
                    ),
                    inline=False
                )
                
                instruction_embed.set_footer(text="🎮 Fish-It Roblox Gift Service • Trusted Seller")
                
                await message.edit(embed=instruction_embed)
                
                await interaction.followup.send(
                    f"✅ **Item berhasil ditambahkan!**\n\n"
                    f"**Kode:** `{code}`\n"
                    f"**Nama:** {name}\n"
                    f"**Harga:** {robux} R$ • {format_idr(price_idr)}\n\n"
                    f"📌 Display di #open-ticket sudah auto-update!\n"
                    f"💡 Total item sekarang: {len(items)}",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.followup.send(
                f"✅ Item **{name}** berhasil ditambahkan ({robux} R$ • {format_idr(price_idr)})\n\n"
                f"⚠️ Gagal update display: {e}",
                ephemeral=True
            )
    else:
        await interaction.followup.send(
            f"✅ **Item berhasil ditambahkan!**\n\n"
            f"**Kode:** `{code}`\n"
            f"**Nama:** {name}\n"
            f"**Harga:** {robux} R$ • {format_idr(price_idr)}",
            ephemeral=True
        )
    
    # Log action
    db.log_action(
        guild_id=interaction.guild.id,
        user_id=interaction.user.id,
        action="add_item",
        details=f"Added: {name} ({robux} R$)"
    )


# --- Slash Command: /remove-item ---
@client.tree.command(
    name="remove-item",
    description="[OWNER] Hapus item dari katalog"
)
@app_commands.describe(
    item="Pilih item yang akan dihapus"
)
@app_commands.default_permissions(administrator=True)
@owner_only()
async def remove_item_from_catalog(interaction: discord.Interaction, item: str):
    """Hapus item dari katalog"""
    await interaction.response.defer(ephemeral=True)
    
    # Get item data
    item_data = db.get_item_price(interaction.guild.id, item)
    
    if not item_data:
        await interaction.followup.send("❌ Item tidak ditemukan.", ephemeral=True)
        return
    
    # Delete item
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM item_prices 
        WHERE guild_id = ? AND item_code = ?
    """, (str(interaction.guild.id), item))
    conn.commit()
    conn.close()
    
    # Auto-update setup-ticket embed if exists
    setup_data = db.get_ticket_setup_message(interaction.guild.id)
    
    if setup_data:
        try:
            channel = interaction.guild.get_channel(setup_data['channel_id'])
            if channel:
                message = await channel.fetch_message(setup_data['message_id'])
                
                # Get remaining items
                items = db.get_all_items(interaction.guild.id)
                rate = db.get_robux_rate(interaction.guild.id)
                
                # Recreate embed
                instruction_embed = discord.Embed(
                    title="🎫 Open Ticket - Panduan",
                    description=f"Selamat datang! Gift Fish-It Roblox dengan rate **Rp{rate}/Robux**",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                instruction_embed.add_field(
                    name="📝 Cara Buka Ticket",
                    value=(
                        "**1.** Klik tombol **Create Ticket** di bawah\n\n"
                        "**2.** Input username game Anda (min 3 karakter)\n"
                        "**Contoh:** `AbuyyXZ777`\n\n"
                        "**3.** Bot akan create private ticket channel\n\n"
                        "**4.** Lihat list item & harga di ticket channel\n\n"
                        "**5.** Gunakan `/add` untuk order item\n\n"
                        "**6.** Upload bukti pembayaran (auto-detect)"
                    ),
                    inline=False
                )
                
                instruction_embed.add_field(
                    name="💳 Pembayaran",
                    value="Admin akan berikan **QRIS** di ticket Anda",
                    inline=False
                )
                
                instruction_embed.add_field(
                    name="⚡ Penting",
                    value=(
                        "• 1 user hanya bisa punya 1 ticket aktif\n"
                        "• Upload bukti transfer ASLI (tidak boleh edit)\n"
                        "• Button akan tetap ada meski bot restart\n"
                        "• Gunakan `/add` di ticket untuk order"
                    ),
                    inline=False
                )
                
                instruction_embed.set_footer(text="🎮 Fish-It Roblox Gift Service • Trusted Seller")
                
                await message.edit(embed=instruction_embed)
                
                await interaction.followup.send(
                    f"✅ **Item berhasil dihapus!**\n\n"
                    f"**Nama:** {item_data['name']}\n"
                    f"**Harga:** {item_data['robux']} R$ • {format_idr(item_data['price_idr'])}\n\n"
                    f"📌 Display di #open-ticket sudah auto-update!\n"
                    f"💡 Total item sekarang: {len(items)}",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.followup.send(
                f"✅ Item **{item_data['name']}** berhasil dihapus\n\n"
                f"⚠️ Gagal update display: {e}",
                ephemeral=True
            )
    else:
        await interaction.followup.send(
            f"✅ **Item berhasil dihapus!**\n\n"
            f"**Nama:** {item_data['name']}\n"
            f"**Harga:** {item_data['robux']} R$ • {format_idr(item_data['price_idr'])}",
            ephemeral=True
        )
    
    # Log action
    db.log_action(
        guild_id=interaction.guild.id,
        user_id=interaction.user.id,
        action="remove_item",
        details=f"Removed: {item_data['name']} ({item_data['robux']} R$)"
    )


@remove_item_from_catalog.autocomplete('item')
async def remove_item_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    """Autocomplete untuk /remove-item"""
    try:
        items = db.get_all_items(interaction.guild.id)
        
        # Filter berdasarkan input user
        if current:
            items = [item for item in items if current.lower() in item['name'].lower()]
        
        # Return max 25 items
        return [
            app_commands.Choice(
                name=f"{item['name']} ({item['robux']} R$ • Rp{item['price_idr']:,})",
                value=item['code']
            )
            for item in items[:25]
        ]
    except Exception as e:
        print(f"Error in autocomplete: {e}")
        return []


# --- Slash Command: /setup-leaderboard ---
@client.tree.command(
    name="setup-leaderboard",
    description="[OWNER] Setup message leaderboard di channel #lb-rich-daily yang akan auto-update setiap 2 jam."
)
@owner_only()
async def setup_leaderboard(interaction: discord.Interaction):
    """Setup message leaderboard yang auto-update"""
    await interaction.response.defer(ephemeral=True)
    
    # Cari channel #lb-rich-daily
    lb_channel = discord.utils.get(interaction.guild.text_channels, name="lb-rich-daily")
    
    if not lb_channel:
        await interaction.followup.send(
            "❌ Channel `#lb-rich-daily` tidak ditemukan!\n"
            "Buat channel dengan nama `lb-rich-daily` terlebih dahulu.",
            ephemeral=True
        )
        return
    
    try:
        # Cek apakah sudah ada message leaderboard lama
        existing_msg = db.get_leaderboard_message(interaction.guild.id)
        if existing_msg:
            try:
                # Hapus message lama
                old_channel = interaction.guild.get_channel(existing_msg['channel_id'])
                if old_channel:
                    old_message = await old_channel.fetch_message(existing_msg['message_id'])
                    await old_message.delete()
                    print(f"🗑️ Deleted old leaderboard message")
            except:
                pass
        
        # Generate embed leaderboard
        embed = await client.generate_leaderboard_embed(interaction.guild)
        
        # Post message baru ke channel
        message = await lb_channel.send(embed=embed)
        
        # Simpan message ID baru ke database
        db.set_leaderboard_message(interaction.guild.id, lb_channel.id, message.id)
        
        await interaction.followup.send(
            f"✅ Leaderboard berhasil di-setup di {lb_channel.mention}!\n"
            f"🔄 Message akan auto-update setiap 2 jam.\n"
            f"📊 Message ID: `{message.id}`",
            ephemeral=True
        )
        
        print(f"✅ Leaderboard setup di {interaction.guild.name} - Channel: {lb_channel.name}")
        
    except discord.Forbidden:
        await interaction.followup.send(
            f"❌ Bot tidak punya permission untuk kirim message di {lb_channel.mention}!",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /approve-mm ---
@client.tree.command(
    name="approve-mm",
    description="[ADMIN] Approve middleman transaction dan release dana ke seller."
)
@app_commands.default_permissions(administrator=True)
async def approve_mm(interaction: discord.Interaction):
    try:
        ticket = db.get_ticket_by_channel(interaction.channel.id)
        
        if not ticket:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di middleman ticket channel.", ephemeral=True)
            return
        
        if ticket.get('ticket_type') != 'middleman':
            await interaction.response.send_message("❌ Ini bukan middleman ticket. Gunakan `/approve-ticket` untuk ticket purchase.", ephemeral=True)
            return
        
        if ticket['status'] != 'open':
            await interaction.response.send_message("❌ Ticket ini sudah ditutup.", ephemeral=True)
            return
        
        # Verify buyer has submitted proof
        if not ticket.get('proof_url'):
            await interaction.response.send_message("❌ Buyer belum upload bukti transfer!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get ticket details
        deal_price = ticket.get('deal_price', 0)
        mm_fee = ticket.get('mm_fee', 0)
        buyer_id = ticket['user_id']
        seller_username = ticket.get('seller_username', 'Unknown Seller')
        fee_payer = ticket.get('fee_payer', 'buyer')
        
        # Calculate payout based on fee_payer
        if fee_payer == 'buyer':
            # Buyer paid deal + fee, seller gets full deal price
            seller_payout = deal_price
            buyer_paid = deal_price + mm_fee
        elif fee_payer == 'seller':
            # Buyer paid only deal price, seller gets deal - fee
            seller_payout = deal_price - mm_fee
            buyer_paid = deal_price
        else:  # split
            # Buyer paid deal + half fee, seller gets deal - half fee
            split_fee = mm_fee // 2
            remaining_fee = mm_fee - split_fee
            seller_payout = deal_price - remaining_fee
            buyer_paid = deal_price + split_fee
        
        # Close ticket
        db.close_ticket(ticket['id'], interaction.user.id)
        
        # Update stats untuk buyer (bukan seller, karena seller dapat dari middleman)
        db.update_user_stats(interaction.guild.id, int(buyer_id), deal_price)
        db.add_transaction(
            guild_id=interaction.guild.id,
            user_id=int(buyer_id),
            amount=deal_price,
            category="middleman_buyer",
            notes=f"Middleman ticket #{ticket['ticket_number']:04d} - {ticket.get('item_description', 'Item')}",
            recorded_by=interaction.user.id
        )
        
        # Send completion message
        completion_embed = discord.Embed(
            title="✅ Transaksi Middleman Berhasil!",
            description=f"Ticket #{ticket['ticket_number']:04d} telah diselesaikan oleh {interaction.user.mention}",
            color=0x00FF00,
            timestamp=datetime.now()
        )
        
        completion_embed.add_field(
            name="📦 Detail Transaksi",
            value=(
                f"**Item:** {ticket.get('item_description', 'N/A')}\n"
                f"**Harga Deal:** Rp{deal_price:,}\n"
                f"**Fee Middleman:** Rp{mm_fee:,}\n"
                f"**Fee dibayar:** {fee_payer.title()}"
            ),
            inline=False
        )
        
        completion_embed.add_field(
            name="👤 Buyer",
            value=f"<@{buyer_id}>",
            inline=True
        )
        
        completion_embed.add_field(
            name="👤 Seller",
            value=f"`{seller_username}`",
            inline=True
        )
        
        completion_embed.add_field(
            name="\u200b",
            value="\u200b",
            inline=True
        )
        
        completion_embed.add_field(
            name="💰 Payout Info",
            value=(
                f"**Buyer bayar:** Rp{buyer_paid:,}\n"
                f"**Seller terima:** Rp{seller_payout:,}\n"
                f"**Fee Middleman:** Rp{mm_fee:,}\n\n"
                f"*Admin: Transfer Rp{seller_payout:,} ke seller*"
            ),
            inline=False
        )
        
        completion_embed.set_footer(
            text=f"Approved by {interaction.user.name} • Ticket closed",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.channel.send(embed=completion_embed)
        
        await interaction.followup.send(
            f"✅ **Middleman transaksi berhasil diapprove!**\n\n"
            f"📌 Ticket #{ticket['ticket_number']:04d} ditutup\n"
            f"💰 Seller payout: **Rp{seller_payout:,}**\n"
            f"💵 Fee middleman: **Rp{mm_fee:,}**\n\n"
            f"⚠️ **JANGAN LUPA:** Transfer Rp{seller_payout:,} ke seller `{seller_username}`!",
            ephemeral=True
        )
        
        # Log action
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="approve_mm_ticket",
            details=f"Ticket #{ticket['ticket_number']:04d} - Seller payout: Rp{seller_payout:,} - Fee: Rp{mm_fee:,}"
        )
        
        # Auto-delete channel after 30 seconds
        await asyncio.sleep(30)
        try:
            await interaction.channel.delete()
        except:
            pass
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Slash Command: /reject-mm ---
@client.tree.command(
    name="reject-mm",
    description="[ADMIN] Reject middleman transaction."
)
@app_commands.default_permissions(administrator=True)
async def reject_mm(interaction: discord.Interaction, reason: str = "Bukti tidak valid"):
    try:
        ticket = db.get_ticket_by_channel(interaction.channel.id)
        
        if not ticket:
            await interaction.response.send_message("❌ Command ini hanya bisa digunakan di middleman ticket channel.", ephemeral=True)
            return
        
        if ticket.get('ticket_type') != 'middleman':
            await interaction.response.send_message("❌ Ini bukan middleman ticket. Gunakan `/reject-ticket` untuk ticket purchase.", ephemeral=True)
            return
        
        if ticket['status'] != 'open':
            await interaction.response.send_message("❌ Ticket ini sudah ditutup.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Close ticket
        db.close_ticket(ticket['id'], interaction.user.id)
        
        # Send rejection message
        reject_embed = discord.Embed(
            title="❌ Transaksi Middleman Ditolak",
            description=f"Ticket #{ticket['ticket_number']:04d} telah ditolak oleh {interaction.user.mention}",
            color=0xFF0000,
            timestamp=datetime.now()
        )
        
        reject_embed.add_field(
            name="📋 Alasan",
            value=f"`{reason}`",
            inline=False
        )
        
        reject_embed.add_field(
            name="ℹ️ Info",
            value=(
                "Transaksi middleman dibatalkan.\n"
                "Jika ada dana yang sudah ditransfer, hubungi admin untuk refund."
            ),
            inline=False
        )
        
        reject_embed.set_footer(
            text=f"Rejected by {interaction.user.name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.channel.send(f"<@{ticket['user_id']}>", embed=reject_embed)
        
        await interaction.followup.send(
            f"✅ Middleman ticket #{ticket['ticket_number']:04d} berhasil direject!\n"
            f"Channel akan dihapus dalam 30 detik.",
            ephemeral=True
        )
        
        # Log action
        db.log_action(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            action="reject_mm_ticket",
            details=f"Ticket #{ticket['ticket_number']:04d} - Reason: {reason}"
        )
        
        # Auto-delete channel after 30 seconds
        await asyncio.sleep(30)
        try:
            await interaction.channel.delete()
        except:
            pass
            
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


# --- Jalankan Bot ---
if __name__ == '__main__':
    try:
        # Gunakan TOKEN yang sudah dimuat dari .env
        client.run(TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Token bot tidak valid. Cek kembali token di file .env.")
    except Exception as e:
        print(f"❌ ERROR: Terjadi kesalahan saat menjalankan bot: {e}")

