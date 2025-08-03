package com.kirlewai.agent

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView

/**
 * RecyclerView adapter for the chat interface
 * Handles both user and AI agent messages
 */
class ChatAdapter(val messages: MutableList<ChatMessage>) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {
    
    companion object {
        private const val VIEW_TYPE_USER = 1
        private const val VIEW_TYPE_AGENT = 2
    }
    
    data class ChatMessage(
        val text: String,
        val isUser: Boolean,
        val timestamp: Long = System.currentTimeMillis()
    )
    
    override fun getItemViewType(position: Int): Int {
        return if (messages[position].isUser) VIEW_TYPE_USER else VIEW_TYPE_AGENT
    }
    
    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        return when (viewType) {
            VIEW_TYPE_USER -> {
                val view = LayoutInflater.from(parent.context)
                    .inflate(R.layout.item_user_message, parent, false)
                UserMessageViewHolder(view)
            }
            VIEW_TYPE_AGENT -> {
                val view = LayoutInflater.from(parent.context)
                    .inflate(R.layout.item_agent_message, parent, false)
                AgentMessageViewHolder(view)
            }
            else -> throw IllegalArgumentException("Unknown view type: $viewType")
        }
    }
    
    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = messages[position]
        when (holder) {
            is UserMessageViewHolder -> holder.bind(message)
            is AgentMessageViewHolder -> holder.bind(message)
        }
    }
    
    override fun getItemCount(): Int = messages.size
    
    /**
     * Add a new message to the chat
     */
    fun addMessage(message: ChatMessage) {
        messages.add(message)
        notifyItemInserted(messages.size - 1)
    }
    
    /**
     * Add a user message
     */
    fun addUserMessage(text: String) {
        addMessage(ChatMessage(text, isUser = true))
    }
    
    /**
     * Add an agent message
     */
    fun addAgentMessage(text: String) {
        addMessage(ChatMessage(text, isUser = false))
    }
    
    /**
     * Clear all messages
     */
    fun clearMessages() {
        val size = messages.size
        messages.clear()
        notifyItemRangeRemoved(0, size)
    }
    
    /**
     * ViewHolder for user messages (right-aligned, blue)
     */
    class UserMessageViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val messageText: TextView = itemView.findViewById(R.id.userMessageText)
        
        fun bind(message: ChatMessage) {
            messageText.text = message.text
        }
    }
    
    /**
     * ViewHolder for agent messages (left-aligned, gray)
     */
    class AgentMessageViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        private val messageText: TextView = itemView.findViewById(R.id.agentMessageText)
        
        fun bind(message: ChatMessage) {
            messageText.text = message.text
        }
    }
}