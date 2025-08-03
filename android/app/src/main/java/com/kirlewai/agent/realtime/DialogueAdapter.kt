package com.kirlewai.agent.realtime

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.kirlewai.agent.R

class DialogueAdapter(private val dialogue: MutableList<String>) : RecyclerView.Adapter<DialogueAdapter.ViewHolder>() {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.dialogue_item, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        holder.textView.text = dialogue[position]
    }

    override fun getItemCount() = dialogue.size

    fun addMessage(message: String) {
        dialogue.add(message)
        notifyItemInserted(dialogue.size - 1)
    }

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val textView: TextView = itemView.findViewById(R.id.dialogueText)
    }
}